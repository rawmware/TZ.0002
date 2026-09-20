"""The shared command layer (terminal and desktop UI), session helpers, and the B5-B7 fixes."""
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from app.tz_agent import Agent
from app.tz_terminal import Hardware, Terminal

GB = 2**30
TAGS = {'models': [
    {'name': 'tz-agent:latest', 'size': int(2.5 * GB)},
    {'name': 'qwen3:4b', 'size': int(2.5 * GB)},
    {'name': 'qwen3:4b-instruct-2507-q4_K_M', 'size': int(2.5 * GB)},
    {'name': 'gemma3:1b', 'size': int(0.8 * GB)},
    {'name': 'gemma4:26b', 'size': 16 * GB},
    {'name': 'qwen3.6:latest', 'size': 22 * GB},
]}


class FakeHardware:
    def __init__(self, vram): self.vram = vram
    def vram_total(self): return self.vram


class FakeTerminal:
    """Just enough of Terminal for /use: the VRAM probe."""
    def __init__(self, vram): self.hardware = FakeHardware(vram)


class CommandTests(unittest.TestCase):
    def setUp(self):
        os.environ['TZ_NO_WARMUP'] = '1'
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.output = []
        self.agent = Agent(self.root, emit=lambda s='', **kw: self.output.append(str(s)), confirm=lambda _: False)
        self.tags = patch.object(self.agent, 'api', return_value=TAGS)
        self.tags.start()

    def tearDown(self):
        self.tags.stop()
        self.agent.preview.close()
        self.tmp.cleanup()

    # ------------------------------------------------------------------ /use

    def test_use_resolves_spaces_and_case(self):
        for text in ('/use qwen 3.6', '/use qwen3.6', '/use Qwen3.6:LATEST', '/use qwen3.6:latest'):
            self.assertEqual(self.agent.command(text)['model'], 'qwen3.6:latest', text)
        self.assertEqual(self.agent.model, 'qwen3.6:latest')
        self.assertEqual(self.agent.task_model, 'qwen3.6:latest')
        self.assertEqual(self.agent.routing, 'manual')
        self.assertIn('Using qwen3.6:latest', self.output)

    def test_use_prefix_matches_one_family(self):
        self.assertEqual(self.agent.command('/use gemma4')['model'], 'gemma4:26b')
        self.assertEqual(self.agent.command('/use tz-agent')['model'], 'tz-agent:latest')

    def test_use_ambiguous_and_missing(self):
        with self.assertRaisesRegex(ValueError, 'Ambiguous model: .*qwen3:4b.*qwen3.6:latest'):
            self.agent.command('/use qwen3')
        with self.assertRaisesRegex(ValueError, 'not installed'):
            self.agent.command('/use nothere')
        with self.assertRaises(ValueError): self.agent.command('/use')
        self.assertEqual(self.agent.model, 'tz-agent:latest')

    def test_vram_warning_declined_keeps_model(self):
        self.agent.terminal = FakeTerminal(8 * GB)
        asked = []
        self.agent.confirm = lambda q: asked.append(q) or False
        with self.assertRaisesRegex(ValueError, 'declined'):
            self.agent.command('/use qwen3.6')
        self.assertEqual(len(asked), 1)
        self.assertIn('GB', asked[0])
        self.assertIn('22 GB', asked[0])
        self.assertIn('8 GB VRAM', asked[0])
        self.assertIn('90s timeout', asked[0])
        self.assertEqual(self.agent.model, 'tz-agent:latest')

    def test_vram_warning_accepted_switches(self):
        self.agent.terminal = FakeTerminal(8 * GB)
        asked = []
        self.agent.confirm = lambda q: asked.append(q) or True
        self.assertEqual(self.agent.command('/use qwen3.6')['model'], 'qwen3.6:latest')
        self.assertEqual(len(asked), 1)
        self.assertIn('GB', asked[0])
        self.assertEqual(self.agent.model, 'qwen3.6:latest')

    def test_small_model_or_unknown_vram_never_asks(self):
        self.agent.terminal = FakeTerminal(8 * GB)
        self.agent.confirm = lambda q: self.fail('should not ask for a model that fits')
        self.agent.command('/use qwen3:4b')
        self.agent.terminal = FakeTerminal(None)
        self.agent.command('/use qwen3.6')
        self.assertEqual(self.agent.model, 'qwen3.6:latest')

    # ----------------------------------------------------------------- /auto

    def test_auto_restores_default_task_model(self):
        self.agent.command('/use gemma4:26b')
        self.assertEqual(self.agent.task_model, 'gemma4:26b')
        result = self.agent.command('/auto')
        self.assertEqual(result, {'routing': 'auto', 'task_model': 'tz-agent:latest'})
        self.assertEqual(self.agent.routing, 'auto')
        self.assertEqual(self.agent.task_model, 'tz-agent:latest')
        self.assertEqual(self.agent.model, 'tz-agent:latest')
        self.assertEqual(self.agent.default_model, 'tz-agent:latest')
        self.assertEqual(self.agent.model_description, 'tz-agent:latest')
        self.assertIn('Routing: AUTO · task model tz-agent:latest', self.output)

    def test_fast_and_code_still_reach_turn(self):
        self.assertEqual(self.agent.command('/fast')['routing'], 'fast')
        self.assertEqual(self.agent.command('/code')['routing'], 'code')

    # --------------------------------------------------------------- /models

    def test_models_filter(self):
        names = [m['name'] for m in self.agent.command('/models qwen')['models']]
        self.assertEqual(names, ['qwen3:4b', 'qwen3:4b-instruct-2507-q4_K_M', 'qwen3.6:latest'])
        self.assertEqual(len(self.output), 3)
        self.assertTrue(all('GB' in line for line in self.output))
        self.assertEqual(len(self.agent.command('/models')['models']), 6)
        self.assertEqual(self.agent.command('/models GEMMA')['models'][0]['name'], 'gemma3:1b')
        self.assertEqual(self.agent.command('/models zzz')['models'], [])

    # ------------------------------------------------------------ plumbing

    def test_busy_lock_is_raised_and_released(self):
        held, release = threading.Event(), threading.Event()

        def holder():
            with self.agent.lock:
                held.set()
                release.wait(5)

        thread = threading.Thread(target=holder, daemon=True)
        thread.start()
        held.wait(5)
        try:
            with self.assertRaisesRegex(RuntimeError, 'busy'): self.agent.command('/tools')
        finally:
            release.set()
            thread.join(5)
        self.assertEqual(self.agent.command('/tools')['tools'][0], 'file_read')
        self.assertFalse(self.agent.lock.locked())

    def test_lock_released_after_error(self):
        with self.assertRaises(ValueError): self.agent.command('/use nothere')
        self.assertFalse(self.agent.lock.locked())
        with self.assertRaisesRegex(ValueError, 'Unknown command'): self.agent.command('/nosuch')
        self.assertFalse(self.agent.lock.locked())

    def test_help_status_tools_and_clear_without_terminal(self):
        self.agent.label = 'roman'
        result = self.agent.command('/help')
        self.assertTrue(result['help'].startswith('roman - local task agent'))
        for item in ('/ui [close|always|never|ask]', '/sessions', '/resume ID', '/new', '/models [filter]'):
            self.assertIn(item, result['help'])
        status = self.agent.command('/status')
        self.assertEqual(status['label'], 'roman')
        self.assertEqual(status['session'], self.agent.id)
        self.assertIn('roman | SYSTEM', ''.join(self.output))
        self.assertIn('file_write', self.agent.command('/tools')['tools'])
        self.agent.messages = [{'role': 'user', 'content': 'x'}]
        self.assertEqual(self.agent.command('/clear'), {'cleared': True, 'id': self.agent.id})
        self.assertEqual(self.agent.messages, [])

    def test_terminal_only_commands_refuse_without_terminal(self):
        for text in ('/specs', '/hardware', '/verbose'):
            with self.assertRaisesRegex(ValueError, 'terminal'): self.agent.command(text)

    def test_ui_commands_without_module(self):
        import builtins
        real_import = builtins.__import__

        def no_ui(name, *args, **kwargs):
            if name == 'app.tz_ui': raise ImportError('missing')
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=no_ui):
            for text in ('/ui', '/ui always'):
                with self.assertRaisesRegex(ValueError, 'not available'): self.agent.command(text)
            self.assertEqual(self.agent.command('/ui close'), {'closed': False})
        with self.assertRaisesRegex(ValueError, '/ui'): self.agent.command('/ui sideways')

    # --------------------------------------------------------------- sessions

    def test_sessions_order_titles_and_round_trip(self):
        self.agent.id = '20260918-100000-aaaaaa'
        self.agent.messages = [{'role': 'user', 'content': '  first   question\nhere ' + 'x' * 80},
                               {'role': 'assistant', 'content': 'answer'}]
        self.agent.model = self.agent.task_model = 'qwen3:4b'
        self.agent.routing = 'manual'
        self.agent.save()
        older = Agent(self.root, emit=lambda *a, **k: None)
        older.id = '20260917-090000-bbbbbb'
        older.save()
        older.preview.close()
        found = self.agent.sessions()
        self.assertEqual([s['id'] for s in found], ['20260918-100000-aaaaaa', '20260917-090000-bbbbbb'])
        self.assertTrue(found[0]['current'] and not found[1]['current'])
        self.assertEqual(found[0]['title'], ('first question here ' + 'x' * 80)[:60])
        self.assertEqual(found[0]['turns'], 1)
        self.assertEqual(found[1]['title'], '(empty)')
        self.assertEqual(time.localtime(found[0]['started'])[:6], (2026, 9, 18, 10, 0, 0))
        self.assertGreater(found[0]['started'], found[1]['started'])

        fresh = Agent(self.root, emit=lambda *a, **k: None)
        try:
            self.assertEqual(fresh.resume('20260918-100000-aaaaaa'), {'id': '20260918-100000-aaaaaa', 'turns': 1})
            self.assertEqual(fresh.messages, self.agent.messages)
            self.assertEqual(fresh.id, '20260918-100000-aaaaaa')
            self.assertEqual((fresh.model, fresh.task_model, fresh.routing), ('qwen3:4b', 'qwen3:4b', 'manual'))
            self.assertEqual(fresh.session('current')['messages'], self.agent.messages)
            self.assertEqual(fresh.session('20260917-090000-bbbbbb')['messages'], [])
        finally: fresh.preview.close()

    def test_new_session_and_bad_ids(self):
        self.agent.messages = [{'role': 'user', 'content': 'keep me'}]
        before = self.agent.id
        result = self.agent.new_session()
        self.assertNotEqual(result['id'], before)
        self.assertEqual(self.agent.id, result['id'])
        self.assertEqual(self.agent.messages, [])
        self.assertTrue((self.agent.state / (before + '.json')).is_file(), 'previous session saved first')
        for bad in ('../x', 'a b', '', '20260101-000000-nofile'):
            with self.assertRaises(ValueError): self.agent.resume(bad)
            with self.assertRaises(ValueError): self.agent.session(bad)
        self.assertEqual(self.agent.id, result['id'])

    def test_session_commands_emit(self):
        self.agent.messages = [{'role': 'user', 'content': 'hello'}]
        first = self.agent.id
        self.agent.command('/new')
        self.assertIn('New session ' + self.agent.id, self.output)
        self.agent.command('/resume ' + first)
        self.assertIn(f'Resumed {first} (1 turns)', self.output)
        listed = self.agent.command('/sessions')['sessions']
        self.assertEqual(listed[0]['id'], self.agent.id)
        with self.assertRaises(ValueError): self.agent.command('/resume')


class TerminalHelperTests(unittest.TestCase):
    def setUp(self):
        os.environ['TZ_NO_WARMUP'] = '1'
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Agent(Path(self.tmp.name), emit=lambda *a, **k: None)

    def tearDown(self):
        self.agent.preview.close()
        self.tmp.cleanup()

    def test_yes_no_returns_default_without_reading_stdin(self):
        with patch('sys.stdin', io.StringIO('y\n')), patch('sys.stdout', new_callable=io.StringIO) as out:
            terminal = Terminal(self.agent)
            terminal.enabled = False
            self.assertFalse(terminal.yes_no('q?', default=False))
            self.assertTrue(terminal.yes_no('q?', default=True))
            terminal.close()
            self.assertEqual(out.getvalue(), '')

    def test_yes_no_reads_one_line_when_interactive(self):
        from prompt_toolkit import PromptSession
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        terminal = Terminal(self.agent)
        terminal.enabled = True
        with create_pipe_input() as pipe:
            real = PromptSession
            with patch('prompt_toolkit.PromptSession', lambda **kw: real(input=pipe, output=DummyOutput(), **kw)):
                pipe.send_text('YES\n')
                self.assertTrue(terminal.yes_no('Would you like to open UI?', default=False))
                pipe.send_text('\n')
                self.assertFalse(terminal.yes_no('Would you like to open UI?', default=False))
                pipe.send_text('maybe\nn\n')
                self.assertFalse(terminal.yes_no('q?', default=True))
        terminal.close()

    def test_vram_total(self):
        with patch('app.tz_terminal.helper', return_value='8192\n') as probe:
            hardware = Hardware()
            self.assertEqual(hardware.vram_total(), 8192 * 1024 * 1024)
            self.assertEqual(hardware.vram_total(), 8192 * 1024 * 1024)
            self.assertEqual(probe.call_count, 1, 'cached')
        with patch('app.tz_terminal.helper', return_value=None):
            self.assertIsNone(Hardware().vram_total())
        with patch('app.tz_terminal.helper', return_value='N/A\n'):
            self.assertIsNone(Hardware().vram_total())

    def test_activity_tracks_turn_and_interrupt(self):
        with patch('sys.stdout', new_callable=io.StringIO):
            terminal = Terminal(self.agent)
        terminal.enabled = False
        self.assertFalse(terminal.turn_active)
        with terminal.activity():
            self.assertTrue(terminal.turn_active)
        self.assertFalse(terminal.turn_active)
        self.assertFalse(terminal.interrupted)
        with self.assertRaises(KeyboardInterrupt):
            with terminal.activity(): raise KeyboardInterrupt
        self.assertTrue(terminal.interrupted)
        self.assertFalse(terminal.turn_active)
        terminal.close()

    def test_emit_is_serialized_across_threads(self):
        from rich.console import Console
        with patch('sys.stdout', new_callable=io.StringIO):
            terminal = Terminal(self.agent)
        terminal.enabled = True
        output = io.StringIO()
        terminal.console = Console(file=output, width=80, color_system=None)
        errors = []

        def worker(n):
            try:
                for i in range(50): terminal.emit(f'thread{n} line{i}')
            except Exception as exc: errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
        for t in threads: t.start()
        for t in threads: t.join(10)
        self.assertEqual(errors, [])
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 200)
        self.assertTrue(all(line.startswith('thread') for line in lines))
        terminal.close()

    def test_warm_up_is_skipped_by_env_and_never_raises(self):
        from app.tz_agent import warm_up
        self.assertIsNone(warm_up(self.agent))
        del os.environ['TZ_NO_WARMUP']
        try:
            with patch.object(self.agent, 'api', side_effect=OSError('down')):
                thread = warm_up(self.agent)
                thread.join(5)
                self.assertFalse(thread.is_alive())
        finally: os.environ['TZ_NO_WARMUP'] = '1'


if __name__ == '__main__': unittest.main()
