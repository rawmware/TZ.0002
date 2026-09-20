import contextlib
from datetime import datetime, timezone
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
        self.browser = patch('app.tz_preview.webbrowser.open', return_value=True)
        self.browser.start()

    def tearDown(self):
        self.agent.preview.close()
        self.browser.stop()
        self.tmp.cleanup()

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
            with patch.object(agent, 'local_model'), patch('app.tz_opencode.executable', return_value=sys.executable), patch('app.tz_opencode.subprocess.Popen', side_effect=launch):
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


DDG_HTML = '''<html><body><div id="links">
<div class="result results_links results_links_deep web-result">
 <h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FJames_Gandolfini&amp;rut=abc">James Gandolfini - Wikipedia</a></h2>
 <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FJames_Gandolfini&amp;rut=abc"><b>James</b> John <b>Gandolfini</b> (September 18, 1961 &#x2013; June 19, 2013) was an American actor.</a>
</div>
<div class="result results_links results_links_deep web-result">
 <h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.britannica.com%2Fbiography%2FJames-Gandolfini&amp;rut=def">James Gandolfini | Biography &amp; Facts - Britannica</a></h2>
 <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.britannica.com%2Fbiography%2FJames-Gandolfini&amp;rut=def">American actor, best known for Tony Soprano.</a>
</div></div></body></html>'''

JUNK_HTML = '''<html><body>
<a class="result__a" href="https://current.com/">Current | Mobile Banking</a><a class="result__snippet" href="https://current.com/">Bank with Current and get paid early.</a>
<a class="result__a" href="https://dict.baidu.com/current">current - Baidu dictionary</a><a class="result__snippet" href="https://dict.baidu.com/current">current adj. happening now</a>
<a class="result__a" href="https://en.wikipedia.org/wiki/Electric_current">Electric current - Wikipedia</a><a class="result__snippet" href="https://en.wikipedia.org/wiki/Electric_current">An electric current is a flow of charged particles.</a>
</body></html>'''

BING_RSS = '''<?xml version="1.0" encoding="utf-8" ?><rss version="2.0"><channel><title>Bing</title>
<item><title>James Gandolfini - IMDb</title><link>https://www.imdb.com/name/nm0001254/</link><description>James Gandolfini, Actor: The Sopranos.</description></item>
</channel></rss>'''


class IntentAndToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = Agent(self.root, emit=lambda *a, **kw: None, confirm=lambda _: False)
        self.browser = patch('app.tz_preview.webbrowser.open', return_value=True)
        self.browser.start()

    def tearDown(self):
        self.agent.preview.close()
        self.browser.stop()
        self.tmp.cleanup()

    def test_browser_phrasings_open_google_search_without_model(self):
        cases = {
            'open the browser and look up the time in japan': 'the+time+in+japan',
            'hello can u opent the browser and look up lil waynes most recent track': 'lil+waynes+most+recent+track',
            'open the web browser and type in what time is it in new mexico?': 'what+time+is+it+in+new+mexico',
            'look up james gandolfini in the browser': 'james+gandolfini',
            'google chicken soup recipe in the browser': 'chicken+soup+recipe',
            'please open the browser, search for cats.': 'cats',
            'Open my browser and find out who won the world series': 'who+won+the+world+series',
        }
        with patch.object(self.agent, 'stream', side_effect=AssertionError('No model needed')):
            for text, encoded in cases.items():
                with self.subTest(text=text):
                    self.assertEqual(self.agent.direct(text), ('open_target', {'target': 'https://www.google.com/search?q=' + encoded}))
            for text in ['open the webbrowser', 'open it in the browser for me', 'opent the web rbwoser so i can see it',
                         'open google', 'can you open the browser please']:
                with self.subTest(text=text):
                    self.assertEqual(self.agent.direct(text), ('open_target', {'target': 'https://www.google.com'}))

    def test_open_it_uses_last_search_or_fetch(self):
        self.agent.messages = [{'role': 'user', 'content': 'search lil wayne'},
                               {'role': 'assistant', 'content': 'Tool evidence (data): {"query": "lil wayne", "provider": "DuckDuckGo HTML", "results": []}'}]
        self.assertEqual(self.agent.direct('open it in the browser'), ('open_target', {'target': 'https://www.google.com/search?q=lil+wayne'}))
        self.agent.messages.append({'role': 'tool', 'tool_name': 'fetch_url', 'content': '{"url": "https://example.com/page", "text": "x"}'})
        self.assertEqual(self.agent.direct('open that in the browser')[1]['target'], 'https://example.com/page')
        self.agent.messages.append({'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'web_search', 'arguments': {'query': 'gandolfini'}}}]})
        self.agent.messages.append({'role': 'tool', 'tool_name': 'web_search', 'content': '{"error": "no relevant results", "verified": false}'})
        self.assertEqual(self.agent.direct('google it in the browser')[1]['target'], 'https://www.google.com/search?q=gandolfini')

    def test_url_open_and_fetch_rules_still_work(self):
        self.assertEqual(self.agent.direct('open https://example.com'), ('open_target', {'target': 'https://example.com'}))
        self.assertEqual(self.agent.direct('read https://example.com')[0], 'fetch_url')
        self.assertIsNone(self.agent.direct('hello'))

    def test_time_intents_are_local(self):
        cases = {'what time is it in japan': 'japan', 'look up the time in albuquerque nm': 'albuquerque nm',
                 'time in portsmouth nh': 'portsmouth nh', 'what time is it': 'here', "what's the time": 'here',
                 'whats the time in new york?': 'new york', 'what is the current time in london right now': 'london'}
        for text, zone in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.agent.direct(text), ('local_time', {'zone': zone}))
        self.assertEqual(self.agent.direct('open the browser and look up the time in japan')[0], 'open_target')

    def test_local_time_tool_with_fixed_clock(self):
        with patch.object(Agent, 'clock', return_value=datetime(2026, 9, 18, 18, 34, tzinfo=timezone.utc)):
            result = self.agent.tool('local_time', {'zone': 'japan'})
            self.assertEqual(result['zone'], 'Asia/Tokyo')
            self.assertEqual(result['time'], '2026-09-19 03:34:00')
            self.assertEqual(result['utc_offset'], '+09:00')
            self.assertEqual(result['clock'], '3:34 AM')
            self.assertEqual(result['day'], 'Saturday')
            self.assertEqual(self.agent.tool('local_time', {'zone': 'Albuquerque NM'})['zone'], 'America/Denver')
            self.assertEqual(self.agent.tool('local_time', {'zone': 'asia/tokyo'})['zone'], 'Asia/Tokyo')
            self.assertEqual(self.agent.tool('local_time', {'zone': 'in portsmouth nh'})['time'], '2026-09-18 14:34:00')
            self.assertEqual(self.agent.tool('local_time', {'zone': 'utc'})['utc_offset'], '+00:00')
            self.assertEqual(self.agent.tool('local_time', {'zone': 'here'})['place'], 'here')
        with self.assertRaisesRegex(ValueError, 'open_target'):
            self.agent.tool('local_time', {'zone': 'atlantis'})

    def test_search_parses_duckduckgo_and_unwraps_links(self):
        with patch('app.tz_agent.get_url', return_value=('u', 'text/html', DDG_HTML)):
            result = self.agent.tool('web_search', {'query': 'James Gandolfini biography'})
        self.assertEqual(result['provider'], 'DuckDuckGo HTML')
        self.assertEqual(result['results'][0], {'title': 'James Gandolfini - Wikipedia', 'url': 'https://en.wikipedia.org/wiki/James_Gandolfini',
                                                'snippet': 'James John Gandolfini (September 18, 1961 – June 19, 2013) was an American actor.'})
        self.assertEqual(result['results'][1]['url'], 'https://www.britannica.com/biography/James-Gandolfini')
        self.assertEqual(result['results'][1]['title'], 'James Gandolfini | Biography & Facts - Britannica')

    def test_search_relevance_guard_rejects_junk(self):
        with patch('app.tz_agent.get_url', return_value=('u', 'text/html', JUNK_HTML)):
            with self.assertRaisesRegex(ValueError, 'no relevant results'):
                self.agent.tool('web_search', {'query': 'current time in Albuquerque NM'})

    def test_search_falls_back_to_bing_when_duckduckgo_fails(self):
        def fetch(url, timeout=20, headers=None):
            if 'duckduckgo' in url: raise OSError('connection refused')
            return url, 'application/rss+xml', BING_RSS
        with patch('app.tz_agent.get_url', side_effect=fetch):
            result = self.agent.tool('web_search', {'query': 'James Gandolfini biography'})
        self.assertEqual(result['provider'], 'Bing RSS')
        self.assertEqual(result['results'][0]['url'], 'https://www.imdb.com/name/nm0001254/')
        with patch('app.tz_agent.get_url', side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'no results'):
                self.agent.tool('web_search', {'query': 'James Gandolfini biography'})


if __name__ == '__main__': unittest.main()
