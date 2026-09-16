import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from app.tz_agent import Agent
from app.tz_install import register, settings


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = Agent(self.root, emit=lambda *a, **kw: None, confirm=lambda _: False)

    def tearDown(self): self.tmp.cleanup()

    def test_original_path_first_request_reads_without_model(self):
        path = self.root / 'AGENTS.md'
        path.write_text('Do actual work.', encoding='utf-8')
        with patch.object(self.agent, 'stream', side_effect=AssertionError('No model needed')):
            result = self.agent.turn(str(path) + ' read this for me then.')
        self.assertEqual(result['text'], 'Do actual work.')

    def test_read_spaces_unicode_and_excerpts(self):
        path = self.root / 'a b.md'
        path.write_text('Hello Roman — café', encoding='utf-8')
        result = self.agent.turn('/read "' + str(path) + '" 6 5')
        self.assertEqual(result['text'], 'Roman')
        self.assertTrue(result['truncated'])

    def test_read_outside_workspace(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'notes.md'; path.write_text('local')
            self.assertEqual(self.agent.tool('file_read', {'path': str(path)})['text'], 'local')

    def test_url_not_misrouted_to_file(self):
        self.assertEqual(self.agent.direct('read https://example.com')[0], 'fetch_url')

    def test_search_request_is_tool(self):
        result = self.agent.direct('scrape the web to find out what cool things people are doing with codex')
        self.assertEqual(result[0], 'web_search')
        self.assertIn('codex', result[1]['query'])

    def test_create_verify_and_decline_overwrite(self):
        result = self.agent.tool('file_write', {'path': 'hello.html', 'content': '<h1>Hello</h1>'})
        self.assertTrue(result['verified'])
        with self.assertRaisesRegex(ValueError, 'declined'):
            self.agent.tool('file_write', {'path': 'hello.html', 'content': 'replacement'})
        self.assertEqual((self.root / 'hello.html').read_text(), '<h1>Hello</h1>')

    def test_approved_overwrite_is_backed_up(self):
        (self.root / 'a.txt').write_text('old')
        self.agent.confirm = lambda _: True
        self.agent.tool('file_write', {'path': 'a.txt', 'content': 'new'})
        self.assertEqual(next((self.agent.state / 'backups').iterdir()).read_text(), 'old')

    def test_write_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'inside'):
            self.agent.tool('file_write', {'path': '../outside.txt', 'content': 'no'})

    def test_schema_rejects_bad_types(self):
        with self.assertRaises(ValueError): self.agent.tool('file_read', {'path': 3})
        with self.assertRaises(ValueError): self.agent.tool('run_command', {'argv': 'echo hello'})
        with self.assertRaises(ValueError): self.agent.tool('system_info', {'invented': True})

    def test_explicit_program_no_shell(self):
        result = self.agent.tool('run_command', {'argv': [sys.executable, '-c', 'print("hello; literal")']}, explicit=True)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('hello; literal', result['output'])

    def test_generated_command_needs_confirmation(self):
        with self.assertRaisesRegex(ValueError, 'declined'):
            self.agent.tool('run_command', {'argv': [sys.executable, '-c', 'print(1)']})

    def test_native_agent_tool_result_returns_to_model(self):
        replies = [
            {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'file_write', 'arguments': {'path': 'done.txt', 'content': 'done'}}}]},
            {'role': 'assistant', 'content': 'Saved and verified.'},
        ]
        with patch.object(self.agent, 'stream', side_effect=replies) as stream:
            self.agent.turn('Put a short note on disk')
        self.assertEqual((self.root / 'done.txt').read_text(), 'done')
        history = stream.call_args.args[0]
        self.assertEqual(history[-1]['role'], 'tool')
        self.assertTrue(json.loads(history[-1]['content'])['verified'])

    def test_alias_creates_real_command_and_setting(self):
        (self.root / 'tz.py').write_text('print("alias launched TZ")', encoding='utf-8')
        command = register('tz_test_alias', self.root, bin_dir=self.root / 'bin', update_path=False)
        self.assertEqual(settings(self.root)['passcode'], 'tz_test_alias')
        result = subprocess.run([str(command)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('alias launched TZ', result.stdout)

    def test_alias_rejects_shell_syntax(self):
        for name in ['hello & whoami', '../bad', 'cmd', 'python']:
            with self.assertRaises(ValueError): register(name, self.root, update_path=False)

    def test_opencode_route(self):
        with patch('app.tz_opencode.executable', return_value='opencode'), patch('app.tz_opencode.run', return_value={'completed': True}) as run:
            self.agent.turn('build a simple HTML website')
            run.assert_called_once()


class StreamTests(unittest.TestCase):
    def test_opencode_error_even_when_process_exits_zero(self):
        from app.tz_opencode import run
        original = subprocess.Popen
        error = {'type': 'tool_use', 'part': {'tool': 'write', 'state': {'status': 'error', 'error': 'disk full'}}}
        finish = {'type': 'step_finish', 'part': {'reason': 'stop'}}
        script = 'print(' + repr(json.dumps(error)) + '); print(' + repr(json.dumps(finish)) + ')'
        def launch(*a, **kw): return original([sys.executable, '-c', script], **kw)
        with tempfile.TemporaryDirectory() as tmp:
            agent = Agent(tmp, emit=lambda *a, **k: None)
            with patch('app.tz_opencode.executable', return_value=sys.executable), patch('app.tz_opencode.subprocess.Popen', side_effect=launch):
                with self.assertRaisesRegex(RuntimeError, 'disk full'): run(agent, 'write a file')

    def test_timeout_and_truncated_stream_are_not_success(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length', 0)))
                self.send_response(200); self.end_headers()
                if self.path == '/api/show': self.wfile.write(b'{"capabilities":["tools"]}'); return
                self.wfile.write(b'{"message":{"content":"Partial"}}\n'); self.wfile.flush()
                if self.server.slow: time.sleep(0.8)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            agent = Agent(timeout=0.25, emit=lambda *a, **k: None, base_url=f'http://127.0.0.1:{server.server_port}')
            server.slow = True
            started = time.monotonic()
            with self.assertRaises((TimeoutError, OSError)):
                agent.stream([{'role': 'user', 'content': 'test'}])
            self.assertLess(time.monotonic() - started, 1)
            server.slow = False
            with self.assertRaisesRegex(RuntimeError, 'without completion'):
                agent.stream([{'role': 'user', 'content': 'test'}])
        finally: server.shutdown(); server.server_close()


if __name__ == '__main__': unittest.main()
