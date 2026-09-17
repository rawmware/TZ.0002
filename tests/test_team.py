import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.tz_agent import Agent, TOOLS
from app.tz_team import MAX_WORKERS, Team, extract_plan, parse
from app.tz_terminal import Terminal


def reply(content):
    return {'role': 'assistant', 'content': content}


class TeamParsingTests(unittest.TestCase):
    def test_manual_split_and_options(self):
        task, jobs, options = parse('/team --write --slots 2 --workers 4 read README | list files | check python')
        self.assertEqual(jobs, ['read README', 'list files', 'check python'])
        self.assertEqual((options['write'], options['slots'], options['workers']), (True, 2, 4))
        self.assertIn('read README', task)

    def test_planned_task_defaults_to_one_slot_and_read_only(self):
        task, jobs, options = parse('/agents summarize the docs folder')
        self.assertIsNone(jobs)
        self.assertEqual(task, 'summarize the docs folder')
        self.assertEqual((options['write'], options['slots'], options['raw']), (False, 1, False))

    def test_empty_and_oversized_teams_are_rejected(self):
        with self.assertRaises(ValueError): parse('/team')
        with self.assertRaises(ValueError): parse('/team ' + ' | '.join(f'job {i}' for i in range(MAX_WORKERS + 1)))
        with self.assertRaises(ValueError): parse('/team only one job |')

    def test_plan_extraction_requires_real_json(self):
        plan = extract_plan('Sure:\n[{"name": "Doc Reader", "role": "Read the docs."}, {"name": "tester", "role": "Run tests."}]', 3)
        self.assertEqual([p['name'] for p in plan], ['doc-reader', 'tester'])
        with self.assertRaises(ValueError): extract_plan('I would split it into two parts.', 3)
        with self.assertRaises(ValueError): extract_plan('[{"name": "solo", "role": "everything"}]', 3)
        with self.assertRaises(ValueError): extract_plan('[{"name": "x"}, {"role": "y"}]', 3)


class TeamRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.output = []
        self.agent = Agent(self.root, emit=lambda s='', **kw: self.output.append(str(s)), confirm=lambda _: False)
        self.agent.capabilities = ['tools']
        self.local = patch.object(self.agent, 'local_model', return_value=None)
        self.local.start()

    def tearDown(self):
        self.local.stop()
        self.agent.preview.close()
        self.tmp.cleanup()

    def test_worker_is_bounded_to_its_tools_and_context(self):
        self.agent.messages.append({'role': 'user', 'content': 'earlier chat'})
        worker = self.agent.worker('reader', 'Read things.', tools=['file_read'])
        self.assertEqual([t['function']['name'] for t in worker.tools], ['file_read'])
        self.assertEqual(worker.messages, [])
        self.assertEqual(worker.routing, 'manual')
        self.assertEqual(worker.rounds, 4)
        self.assertIn('reader', worker.system)
        with self.assertRaisesRegex(ValueError, 'not available'):
            worker.tool('file_write', {'path': 'x.txt', 'content': 'no'})
        self.assertEqual(len(self.agent.tools), len(TOOLS))

    def test_manual_team_runs_each_worker_once_and_leaves_receipts(self):
        answers = [reply('report one'), reply('report two'), reply('combined answer')]
        with patch.object(self.agent, 'stream', side_effect=answers) as stream:
            receipt = self.agent.turn('/team first job | second job')
        self.assertEqual(stream.call_count, 3)
        self.assertEqual([w['status'] for w in receipt['workers']], ['done', 'done'])
        self.assertEqual(receipt['summary'], 'combined answer')
        self.assertTrue(receipt['verified'])
        # Each worker saw only its own job, plus the lead saw both reports.
        first = stream.call_args_list[0][0][0]
        self.assertEqual(first[-1]['role'], 'user')
        self.assertIn('first job', first[-1]['content'])
        self.assertNotIn('second job', first[-1]['content'])
        self.assertIn('report two', stream.call_args_list[2][0][0][-1]['content'])
        folder = self.root / 'data' / 'tz' / 'teams'
        saved = json.loads((folder / (receipt['team'] + '.json')).read_text(encoding='utf-8'))
        self.assertEqual(saved['summary'], 'combined answer')
        self.assertIn('## Lead summary', (folder / (receipt['team'] + '.md')).read_text(encoding='utf-8'))
        self.assertIn('Team evidence', self.agent.messages[-1]['content'])
        self.assertTrue(any('Team receipts' in line for line in self.output))

    def test_planner_splits_the_task_when_no_manual_split(self):
        plan = json.dumps([{'name': 'reader', 'role': 'Read the README.'}, {'name': 'lister', 'role': 'List files.'}])
        answers = [reply(plan), reply('read it'), reply('listed'), reply('done')]
        with patch.object(self.agent, 'stream', side_effect=answers) as stream:
            receipt = self.agent.turn('/team describe this workspace')
        self.assertEqual([w['name'] for w in receipt['workers']], ['reader', 'lister'])
        self.assertIn('describe this workspace', stream.call_args_list[0][0][0][-1]['content'])
        self.assertEqual(receipt['summary'], 'done')

    def test_planner_failure_is_reported_not_guessed(self):
        with patch.object(self.agent, 'stream', side_effect=[reply('I cannot plan that.')]):
            with self.assertRaisesRegex(ValueError, 'Split the task yourself'):
                self.agent.turn('/team something vague')
        self.assertFalse((self.root / 'data' / 'tz' / 'teams').exists())

    def test_failed_worker_marks_receipt_and_team_unverified(self):
        answers = [reply('ok'), RuntimeError('model exploded'), reply('summary of the one that worked')]
        with patch.object(self.agent, 'stream', side_effect=answers):
            receipt = self.agent.turn('/team good job | bad job')
        self.assertEqual([w['status'] for w in receipt['workers']], ['done', 'failed'])
        self.assertIn('model exploded', receipt['workers'][1]['error'])
        self.assertFalse(receipt['verified'])
        self.assertEqual(receipt['summary'], 'summary of the one that worked')

    def test_cancel_persists_partial_receipts_and_propagates(self):
        with patch.object(self.agent, 'stream', side_effect=[reply('first'), KeyboardInterrupt()]):
            with self.assertRaises(KeyboardInterrupt):
                self.agent.turn('/team one | two | three')
        folder = self.root / 'data' / 'tz' / 'teams'
        saved = json.loads(next(folder.glob('*.json')).read_text(encoding='utf-8'))
        self.assertEqual([w['status'] for w in saved['workers']], ['done', 'canceled', 'canceled'])
        self.assertTrue(saved['canceled'])
        self.assertEqual(saved['summary'], '')

    def test_worker_tool_calls_and_files_are_receipted(self):
        call = {'function': {'name': 'file_write', 'arguments': {'path': 'note.txt', 'content': 'hi'}}}
        answers = [{'role': 'assistant', 'content': '', 'tool_calls': [call]}, reply('wrote note.txt'),
                   reply('nothing to do'), reply('summary')]
        with patch.object(self.agent, 'stream', side_effect=answers):
            receipt = self.agent.turn('/team --write write note.txt | idle')
        writer = receipt['workers'][0]
        self.assertEqual(writer['tools'], ['file_write'])
        self.assertEqual(len(writer['files']), 1)
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), 'hi')

    def test_read_only_team_cannot_write_even_if_the_model_asks(self):
        call = {'function': {'name': 'file_write', 'arguments': {'path': 'x.txt', 'content': 'no'}}}
        answers = [{'role': 'assistant', 'content': '', 'tool_calls': [call]}, reply('could not write'),
                   reply('fine'), reply('summary')]
        with patch.object(self.agent, 'stream', side_effect=answers):
            receipt = self.agent.turn('/team try to write | idle')
        self.assertFalse((self.root / 'x.txt').exists())
        self.assertEqual(receipt['workers'][0]['files'], [])
        self.assertTrue(any('not available' in line for line in self.output))

    def test_parallel_slots_buffer_output_and_still_receipt(self):
        answers = {'alpha': reply('A done'), 'beta': reply('B done')}

        def stream(request):
            text = request[-1]['content']
            if 'Original task' in text: return reply('both done')
            return answers['alpha' if 'alpha' in text else 'beta']

        with patch.object(self.agent, 'stream', side_effect=stream):
            receipt = self.agent.turn('/team --slots 2 alpha job | beta job')
        self.assertEqual({w['status'] for w in receipt['workers']}, {'done'})
        self.assertEqual(receipt['summary'], 'both done')
        self.assertEqual([w['report'] for w in receipt['workers']], ['A done', 'B done'])
        self.assertIn('Team receipts', '\n'.join(self.output))

    def test_raw_option_skips_the_lead(self):
        with patch.object(self.agent, 'stream', side_effect=[reply('one'), reply('two')]) as stream:
            receipt = self.agent.turn('/team --raw a | b')
        self.assertEqual(stream.call_count, 2)
        self.assertEqual(receipt['summary'], '')
        self.assertTrue(receipt['verified'])


class TeamTerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Agent(Path(self.tmp.name), emit=lambda *a, **kw: None)

    def tearDown(self):
        self.agent.preview.close()
        self.tmp.cleanup()

    def test_table_renders_bordered_when_enabled_and_plain_when_not(self):
        from rich.console import Console
        terminal = Terminal(self.agent)
        terminal.enabled = True
        out = io.StringIO()
        terminal.console = Console(file=out, width=80, color_system=None)
        terminal.table('Team plan', ['#', 'Worker', 'Deliverable'], [['1', 'reader', 'Read the README']])
        self.assertIn('Team plan', out.getvalue())
        self.assertIn('reader', out.getvalue())
        terminal.close()
        with patch('sys.stdout', new_callable=io.StringIO) as plain:
            terminal = Terminal(self.agent)
            terminal.table('Team plan', ['#', 'Worker'], [['1', 'reader']])
            terminal.close()
        self.assertNotIn('\x1b', plain.getvalue())
        self.assertIn('reader', plain.getvalue())

    def test_worker_frames_use_the_team_title_and_reset_after_activity(self):
        from rich.console import Console
        terminal = Terminal(self.agent)
        terminal.enabled = True
        out = io.StringIO()
        terminal.console = Console(file=out, width=80, color_system=None)
        self.agent.terminal = terminal
        team = Team(self.agent)
        with terminal.activity():
            team.frame('Worker 1/2  ·  reader')
            team.note('worker 1/2 · reader')
            terminal.emit('hello from the worker\n', end='')
            self.assertEqual(terminal.note, 'worker 1/2 · reader')
            team.frame(None)
        self.assertIn('Worker 1/2', out.getvalue())
        self.assertIsNone(terminal.reply_title)
        self.assertIsNone(terminal.note)
        terminal.close()

    def test_status_line_names_model_route_workspace_and_session(self):
        from rich.console import Console
        terminal = Terminal(self.agent)
        terminal.enabled = True
        terminal.console = Console(file=io.StringIO(), width=60, color_system=None)
        line = terminal.status_line()
        for part in (self.agent.model, self.agent.routing.upper(), Path(self.tmp.name).name, self.agent.id):
            self.assertIn(part, line)
        terminal.hardware.readings = 'CPU [||......] 24%  |  RAM 12.3/32.0 GB  |  GPU0 [|.......] 8%  |  VRAM 1.2/8.0 GB'
        bar = terminal.toolbar()
        self.assertNotIn('\n', bar)
        self.assertLessEqual(len(bar), 60)
        terminal.close()


if __name__ == '__main__': unittest.main()
