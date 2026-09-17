import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.tz_agent import Agent
from app.tz_terminal import Terminal


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output = []
        self.agent = Agent(Path(self.tmp.name), emit=lambda s='', **kw: self.output.append(s))

    def tearDown(self):
        self.agent.preview.close()
        self.tmp.cleanup()

    def test_real_routing_choices_and_manual_pin(self):
        with patch.object(self.agent, 'api', return_value={'models': [{'name': 'gemma3:1b'}]}):
            self.agent.route('hello')
            self.assertEqual(self.agent.model, 'gemma3:1b')
            self.agent.route('implement an application', coding=True)
            self.assertEqual(self.agent.model, self.agent.task_model)
            self.agent.routing = 'manual'
            self.agent.route('hello')
            self.assertEqual(self.agent.model, self.agent.task_model)

    def test_missing_small_model_retains_working_default(self):
        with patch.object(self.agent, 'api', return_value={'models': []}):
            self.agent.route('hello')
        self.assertEqual(self.agent.model, self.agent.task_model)
        self.assertIn('fallback', self.output[-1])

    def test_empty_small_model_falls_back_once(self):
        with patch.object(self.agent, 'api', return_value={'models': [{'name': 'gemma3:1b'}]}), patch.object(
                self.agent, 'stream', side_effect=[RuntimeError('Model returned no answer or tool calls.'),
                {'role': 'assistant', 'content': 'Hello'}]) as stream:
            self.agent.turn('hello')
        self.assertEqual(stream.call_count, 2)
        self.assertEqual(self.agent.model, self.agent.task_model)

    def test_diagnostics_do_not_spam_transcript(self):
        self.agent.astra('real-model', 'completed')
        self.assertEqual(self.output, [])
        self.agent.status()
        self.assertIn('real-model', self.output[-1])
        self.assertNotIn('ASTRA', self.output[-1])

    def test_redirected_output_is_plain(self):
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            terminal = Terminal(self.agent)
            terminal.header()
            terminal.emit('hello')
            terminal.close()
            self.assertNotIn('\x1b', out.getvalue())
            self.assertIn('LOCAL AGENT', out.getvalue())

    def test_interactive_input_with_real_prompt_renderer(self):
        from prompt_toolkit import PromptSession
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        from rich.console import Console
        terminal = Terminal(self.agent)
        with create_pipe_input() as pipe:
            terminal.enabled = True
            terminal.console = Console(file=io.StringIO(), width=60)
            terminal.session = PromptSession(input=pipe, output=DummyOutput(),
                show_frame=True, erase_when_done=True, reserve_space_for_menu=0)
            pipe.send_text('hello\n')
            self.assertEqual(terminal.read(), 'hello')
            self.assertTrue(terminal.enabled)
        terminal.close()

    def test_stream_fragments_remain_together_on_cancel(self):
        from rich.console import Console
        terminal = Terminal(self.agent)
        terminal.enabled = True
        output = io.StringIO()
        terminal.console = Console(file=output, width=80, color_system=None)
        with self.assertRaises(KeyboardInterrupt):
            with terminal.activity():
                terminal.emit('Hello', end='')
                terminal.emit(' world', end='')
                self.assertEqual(terminal.stream_buffer, 'Hello world')
                raise KeyboardInterrupt
        self.assertEqual(output.getvalue().count('Hello world'), 1)
        self.assertEqual(terminal.stream_buffer, '')
        self.assertIsNone(terminal.live)
        terminal.close()


    def make_terminal(self, width=80):
        from rich.console import Console
        terminal = Terminal(self.agent)
        terminal.enabled = True
        output = io.StringIO()
        terminal.console = Console(file=output, width=width, color_system=None)
        return terminal, output

    def test_specs_panel_renders_without_psutil(self):
        import builtins
        real_import = builtins.__import__

        def no_psutil(name, *args, **kwargs):
            if name == 'psutil': raise ImportError('psutil missing')
            return real_import(name, *args, **kwargs)

        terminal, output = self.make_terminal()
        with patch('builtins.__import__', side_effect=no_psutil):
            terminal.specs()
        text = output.getvalue()
        self.assertIn('This machine', text)
        self.assertIn('psutil not installed', text)
        self.assertIn('Python', text)
        self.assertIn('Disk', text)
        terminal.close()

    def test_specs_never_invents_a_gpu_reading(self):
        terminal, output = self.make_terminal()
        with patch('app.tz_terminal.shutil.which', return_value=None), patch.object(
                terminal.hardware, 'windows_query', return_value=[]):
            rows = dict(terminal.hardware.specs(refresh=True))
        self.assertIn('not detected', rows['GPU'])
        terminal.close()

    def test_long_multiline_input_is_echoed_in_full(self):
        from prompt_toolkit import PromptSession
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        terminal, output = self.make_terminal(width=60)
        sentence = 'explain the routing layer ' * 12
        with create_pipe_input() as pipe:
            terminal.session = PromptSession(input=pipe, output=DummyOutput(),
                show_frame=True, erase_when_done=True, reserve_space_for_menu=0)
            pipe.send_text(sentence + '\n')
            self.assertEqual(terminal.read(), sentence)
        echoed = ''.join(c for c in output.getvalue() if c.isalnum())
        self.assertIn(''.join(sentence.split()), echoed)
        terminal.close()

    def test_long_reply_commits_lines_once_and_never_redraws(self):
        terminal, output = self.make_terminal()
        with terminal.activity():
            for i in range(200):
                terminal.emit(f'line {i}\n', end='')
        text = output.getvalue()
        for i in (0, 99, 199):
            self.assertEqual(text.count(f'line {i}\n'), 1)
        self.assertEqual(terminal.stream_buffer, '')
        terminal.close()

    def test_finished_code_block_is_highlighted_without_reprinting(self):
        terminal, output = self.make_terminal()
        with terminal.activity():
            terminal.emit('Here:\n```python\nprint("hi")\n```\ndone\n', end='')
        text = output.getvalue()
        self.assertEqual(text.count('print("hi")'), 1)
        self.assertNotIn('```', text)
        self.assertIn('done', text)
        terminal.close()

    def test_cancel_marks_the_partial_reply(self):
        terminal, output = self.make_terminal()
        with self.assertRaises(KeyboardInterrupt):
            with terminal.activity():
                terminal.emit('half an answer\n', end='')
                raise KeyboardInterrupt
        self.assertIn('canceled, unverified', output.getvalue())
        terminal.close()

    def test_toolbar_stays_one_line(self):
        terminal, _ = self.make_terminal()
        terminal.hardware.readings = 'CPU 10%\nGPU0 5%'
        self.assertNotIn('\n', terminal.toolbar())
        terminal.close()

    def test_verbose_toggle_hides_only_detail_tags(self):
        terminal, output = self.make_terminal()
        terminal.verbose = False
        terminal.emit('[route] AUTO -> gemma3:1b')
        terminal.emit('real answer')
        self.assertNotIn('[route]', output.getvalue())
        self.assertIn('real answer', output.getvalue())
        terminal.close()

    def test_help_and_specs_are_plain_when_redirected(self):
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            terminal = Terminal(self.agent)
            terminal.help('TZ - local task agent\n  /status   Show runtime')
            terminal.specs()
            terminal.close()
            self.assertNotIn('\x1b', out.getvalue())
            self.assertIn('/status', out.getvalue())
            self.assertIn('Python:', out.getvalue())


if __name__ == '__main__': unittest.main()
