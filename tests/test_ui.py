import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from app.tz_ui import Desktop, open_mode, set_open_mode, ui_config, write_ui_config

DEFAULTS = {
    'open': 'ask', 'wallpaper': '#008080', 'wallpaper_image': '', 'chime': False, 'removed': [],
    'presets': [
        {'id': 'time-japan', 'name': 'Time in Japan', 'phrase': 'what time is it in japan', 'mode': 'ask', 'icon': 'clock'},
        {'id': 'latest-news', 'name': 'Latest news', 'phrase': 'latest news', 'mode': 'browser', 'icon': 'search'},
    ],
}


class FakeAgent:
    def __init__(self, workspace):
        self.label, self.model, self.model_description = 'TZ', 'tz-agent:latest', 'tz-agent:latest'
        self.task_model, self.routing, self.id = 'tz-agent:latest', 'auto', '20260919-000000-abcdef'
        self.workspace = Path(workspace)
        self.state = self.workspace / 'data' / 'tz'
        self.lock = threading.Lock()
        self.emit = lambda *a, **k: None
        self.confirm = lambda q: False
        self.calls, self.results, self.tools = [], [], []
        self.fail_api = False

    def command(self, text):
        self.calls.append(text)
        if text == 'slow': time.sleep(0.5)
        if text == 'confirm':
            answer = self.confirm('Replace?'); self.results.append(answer); return answer
        if text == 'boom': raise ValueError('bad')
        return {'ok': text}

    def sessions(self): return [{'id': self.id, 'started': 0.0, 'title': 'hi', 'turns': 1, 'current': True}]

    def session(self, sid):
        if sid != self.id and sid != 'other': raise ValueError('No such session: ' + sid)
        return {'id': sid, 'messages': [{'role': 'user', 'content': 'hi'}]}

    def resume(self, sid):
        if sid != 'other': raise ValueError('No such session: ' + sid)
        self.id = sid; return {'id': sid, 'turns': 2}

    def new_session(self):
        self.id = 'fresh-id'; return {'id': self.id}

    def tool(self, name, args, explicit=False):
        self.tools.append((name, args, explicit))
        return {'opened': args['target']} if name == 'open_target' else {}

    def api(self, path, body=None):
        if self.fail_api: raise OSError('down')
        return {'models': [{'name': 'tz-agent:latest', 'size': 1234, 'digest': 'x'}, {'name': 'gemma3:1b', 'size': 99}]}


class EventReader:
    """Reads an SSE stream on a thread, collecting each data: JSON object."""

    def __init__(self, url):
        self.events, self.response = [], urllib.request.urlopen(url, timeout=5)
        self.thread = threading.Thread(target=self.run, daemon=True); self.thread.start()

    def run(self):
        try:
            while True:
                line = self.response.readline()
                if not line: break
                if line.startswith(b'data: '): self.events.append(json.loads(line[6:]))
        except (OSError, ValueError):
            pass

    def wait_for(self, kind, timeout=3, **match):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for e in self.events:
                if e.get('type') == kind and all(e.get(k) == v for k, v in match.items()): return e
            time.sleep(0.02)
        raise AssertionError(f'No {kind} event in {[e.get("type") for e in self.events]}')

    def close(self):
        try: self.response.close()
        except OSError: pass


def wait_until(check, timeout=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check(): return True
        time.sleep(0.02)
    return False


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'config').mkdir()
        (self.root / 'config' / 'ui.defaults.json').write_text(json.dumps(DEFAULTS), encoding='utf-8')
        self.workspace = self.root / 'work'; self.workspace.mkdir()
        self.agent = FakeAgent(self.workspace)
        self.browser = patch('app.tz_ui.webbrowser.open', return_value=True); self.opener = self.browser.start()
        self.desktop = Desktop(self.agent, terminal=None, root=self.root)
        self.url = self.desktop.open()
        self.base = self.url[:-len('ui/')]
        self.readers = []

    def tearDown(self):
        for r in self.readers: r.close()
        self.desktop.close()
        self.browser.stop()
        self.tmp.cleanup()

    # ---- helpers
    def request(self, path, method='GET', body=None, raw=False):
        data = json.dumps(body).encode() if body is not None and not raw else body
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json'} if data is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def get_json(self, path, method='GET', body=None, raw=False):
        status, headers, data = self.request(path, method, body, raw)
        return status, json.loads(data) if data else None

    def events(self):
        reader = EventReader(self.base + 'api/events'); self.readers.append(reader)
        reader.wait_for('hello'); return reader

    # ---- 1
    def test_token_required_and_html_headers(self):
        self.assertEqual(self.opener.call_args[0][0], self.url)
        port = self.url.split(':')[2].split('/')[0]
        for path in (f'http://127.0.0.1:{port}/ui/', f'http://127.0.0.1:{port}/{"0" * 32}/ui/', f'http://127.0.0.1:{port}/{"0" * 32}/api/state'):
            with self.assertRaises(urllib.error.HTTPError) as ctx: urllib.request.urlopen(path, timeout=5)
            self.assertEqual(ctx.exception.code, 404)
        status, headers, data = self.request('ui/')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/html'))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        self.assertIn(b'front end not installed', data)
        self.assertEqual(self.request('ui/../app/tz_ui.py')[0], 404)
        self.assertEqual(self.get_json('api/nope')[0], 404)

    # ---- 2
    def test_state_shape(self):
        status, state = self.get_json('api/state')
        self.assertEqual(status, 200)
        self.assertEqual(set(state), {'label', 'model', 'model_description', 'task_model', 'routing', 'session_id',
                                      'workspace', 'busy', 'specs', 'readings', 'version'})
        self.assertEqual(state['version'], '0.4')
        self.assertEqual(state['specs'], []); self.assertEqual(state['readings'], '')
        self.assertFalse(state['busy']); self.assertEqual(state['session_id'], self.agent.id)

    # ---- 3
    def test_turn_runs_on_worker_and_streams_events(self):
        reader = self.events()
        self.assertEqual(reader.events[0]['version'], '0.4')
        status, body = self.get_json('api/turn', 'POST', {'text': 'hello there'})
        self.assertEqual((status, body), (202, {'accepted': True}))
        self.assertTrue(wait_until(lambda: self.agent.calls == ['hello there']))
        self.assertEqual(reader.wait_for('turn_start')['source'], 'ui')
        self.assertEqual(reader.wait_for('turn_start')['text'], 'hello there')
        self.assertTrue(reader.wait_for('turn_end')['ok'])
        self.assertEqual(reader.wait_for('status')['session_id'], self.agent.id)

    # ---- 4
    def test_turn_busy(self):
        with self.agent.lock:
            self.assertEqual(self.get_json('api/turn', 'POST', {'text': 'x'}), (409, {'error': 'busy'}))
            self.assertTrue(self.get_json('api/state')[1]['busy'])
        self.assertEqual(self.get_json('api/turn', 'POST', {'text': 'x'})[0], 202)

    # ---- 5
    def test_turn_bad_input(self):
        self.assertEqual(self.get_json('api/turn', 'POST', {'text': '  '})[0], 400)
        self.assertEqual(self.get_json('api/turn', 'POST', {})[0], 400)
        self.assertEqual(self.get_json('api/turn', 'POST', b'{not json', raw=True)[0], 400)
        self.assertEqual(self.get_json('api/turn', 'POST', b'[1, 2]', raw=True)[0], 400)
        self.assertEqual(self.agent.calls, [])

    # ---- 6
    def test_confirm_bridge(self):
        reader = self.events()
        self.get_json('api/turn', 'POST', {'text': 'confirm'})
        event = reader.wait_for('confirm')
        self.assertEqual(event['question'], 'Replace?')
        self.assertEqual(self.get_json('api/confirm', 'POST', {'id': 'nope', 'answer': True})[0], 404)
        self.assertEqual(self.get_json('api/confirm', 'POST', {'id': event['id'], 'answer': True}), (200, {'ok': True}))
        self.assertTrue(wait_until(lambda: self.agent.results == [True]))
        self.assertTrue(reader.wait_for('confirm_done', id=event['id'])['answer'])
        self.assertTrue(reader.wait_for('turn_end')['ok'])
        self.assertTrue(wait_until(lambda: self.agent.confirm != self.desktop.confirm_bridge))
        self.assertFalse(self.agent.confirm('later'))

    # ---- 7
    def test_turn_error_reports_turn_end(self):
        reader = self.events()
        lines = []
        self.desktop.original_emit = lambda v='', end='\n', flush=False: lines.append(v)
        self.get_json('api/turn', 'POST', {'text': 'boom'})
        end = reader.wait_for('turn_end')
        self.assertEqual((end['ok'], end['error']), (False, 'bad'))
        self.assertEqual(reader.wait_for('line')['text'], '[incomplete] bad')
        self.assertEqual(lines, ['[incomplete] bad'])

    # ---- 8
    def test_emit_fanout_and_restore(self):
        reader = self.events()
        original_emit, original_command = self.desktop.original_emit, self.desktop.original_command
        self.agent.emit('hello'); self.agent.emit('x', end='')
        self.assertEqual(reader.wait_for('line')['text'], 'hello')
        self.assertEqual(reader.wait_for('stream')['text'], 'x')
        self.agent.command('from terminal')
        self.assertEqual(reader.wait_for('turn_start')['source'], 'terminal')
        self.desktop.close()
        self.assertIs(self.agent.emit, original_emit)
        self.assertEqual(self.agent.command, original_command)
        self.assertTrue(wait_until(lambda: not reader.thread.is_alive()))
        self.desktop.close()  # idempotent

    # ---- 9
    def test_sessions(self):
        reader = self.events()
        self.assertEqual(self.get_json('api/sessions')[1][0]['id'], self.agent.id)
        self.assertEqual(self.get_json('api/sessions/current')[1]['id'], self.agent.id)
        self.assertEqual(self.get_json('api/sessions/other')[1]['id'], 'other')
        self.assertEqual(self.get_json('api/sessions/missing')[0], 404)
        self.assertEqual(self.get_json('api/sessions/bad%20id!')[0], 404)
        with self.agent.lock:
            self.assertEqual(self.get_json('api/sessions/other/resume', 'POST')[0], 409)
            self.assertEqual(self.get_json('api/sessions/new', 'POST')[0], 409)
        self.assertEqual(self.get_json('api/sessions/missing/resume', 'POST')[0], 404)
        self.assertEqual(self.get_json('api/sessions/other/resume', 'POST'), (200, {'id': 'other', 'turns': 2}))
        self.assertEqual(reader.wait_for('session')['id'], 'other')
        self.assertEqual(self.get_json('api/sessions/new', 'POST'), (200, {'id': 'fresh-id'}))
        self.assertEqual(reader.wait_for('session', id='fresh-id')['id'], 'fresh-id')

    # ---- 10
    def test_ui_config_layers(self):
        config = ui_config(self.root)
        self.assertEqual(config['open'], 'ask')
        self.assertEqual([p['id'] for p in config['presets']], ['time-japan', 'latest-news'])
        local = {'passcode': 'Roman', 'ui': {'open': 'always', 'removed': ['latest-news'], 'presets': [
            {'id': 'time-japan', 'name': 'Japan!', 'phrase': 'japan time', 'mode': 'ask', 'icon': 'clock'},
            {'id': 'mine', 'name': 'Mine', 'phrase': 'my thing', 'mode': 'browser', 'icon': 'search'}]}}
        (self.root / 'config' / 'tz.local.json').write_text(json.dumps(local), encoding='utf-8')
        config = ui_config(self.root)
        self.assertEqual(config['open'], 'always')
        self.assertEqual([(p['id'], p['name']) for p in config['presets']], [('time-japan', 'Japan!'), ('mine', 'Mine')])
        self.assertEqual(config['wallpaper'], '#008080')
        self.assertEqual(self.get_json('api/config')[1], config)

    # ---- 11
    def test_write_ui_config(self):
        (self.root / 'config' / 'tz.local.json').write_text(json.dumps({'passcode': 'Roman', 'launcher': 'x'}), encoding='utf-8')
        with self.assertRaises(ValueError) as ctx: write_ui_config({'theme': 'dark'}, self.root)
        self.assertEqual(str(ctx.exception), 'Unknown UI setting: theme')
        for bad in ({'open': 'sometimes'}, {'wallpaper': 'teal'}, {'chime': 'yes'}, {'removed': 'x'},
                    {'presets': [{'id': 'Bad Id', 'name': 'n', 'phrase': 'p', 'mode': 'ask'}]},
                    {'presets': [{'id': 'ok', 'name': 'n', 'phrase': 'p', 'mode': 'fly'}]}, {'presets': 'no'}):
            with self.assertRaises(ValueError): write_ui_config(bad, self.root)
        result = write_ui_config({'wallpaper': '#123ABC', 'chime': True}, self.root)
        self.assertEqual((result['wallpaper'], result['chime']), ('#123ABC', True))
        result = write_ui_config({'presets': [{'id': 'mine', 'name': 'Mine', 'phrase': 'p', 'mode': 'ask', 'icon': 'preset'}]}, self.root)
        self.assertEqual([p['id'] for p in result['presets']], ['time-japan', 'latest-news', 'mine'])
        saved = json.loads((self.root / 'config' / 'tz.local.json').read_text(encoding='utf-8'))
        self.assertEqual((saved['passcode'], saved['launcher']), ('Roman', 'x'))
        self.assertEqual(saved['ui'], {'wallpaper': '#123ABC', 'chime': True,
                                       'presets': [{'id': 'mine', 'name': 'Mine', 'phrase': 'p', 'mode': 'ask', 'icon': 'preset'}]})
        self.assertNotIn('open', saved['ui'])
        status, body = self.get_json('api/config', 'PUT', {'bogus': 1})
        self.assertEqual((status, body), (400, {'error': 'Unknown UI setting: bogus'}))
        self.assertEqual(self.get_json('api/config', 'PUT', {'open': 'never'})[1]['open'], 'never')
        self.assertEqual(self.get_json('api/config', 'PUT', {'open': 'maybe'})[0], 400)
        self.assertEqual(open_mode(self.root), 'never')

    # ---- 12
    def test_open_url(self):
        self.assertEqual(self.get_json('api/open', 'POST', {'url': 'https://example.com'}), (200, {'opened': 'https://example.com'}))
        self.assertEqual(self.agent.tools, [('open_target', {'target': 'https://example.com'}, True)])
        self.assertEqual(self.get_json('api/open', 'POST', {'url': 'file:///x'})[0], 400)
        self.assertEqual(self.get_json('api/open', 'POST', {})[0], 400)
        self.assertEqual(len(self.agent.tools), 1)

    # ---- 13
    def test_files_and_file(self):
        (self.workspace / 'zeta').mkdir(); (self.workspace / 'alpha.txt').write_text('hi there', encoding='utf-8')
        (self.workspace / 'pic.png').write_bytes(b'\x89PNG\r\n\x1a\n'); (self.workspace / 'tool.exe').write_bytes(b'MZ')
        status, listing = self.get_json('api/files')
        self.assertEqual(status, 200); self.assertEqual(listing['path'], '.')
        self.assertEqual([(e['name'], e['dir'], e['size']) for e in listing['entries']],
                         [('zeta', True, 0), ('alpha.txt', False, 8), ('pic.png', False, 8), ('tool.exe', False, 2)])
        self.assertEqual(self.get_json('api/files?path=zeta')[1], {'path': 'zeta', 'entries': []})
        self.assertEqual(self.get_json('api/files?path=..')[0], 404)
        self.assertEqual(self.get_json('api/files?path=alpha.txt')[0], 404)
        status, headers, data = self.request('api/file?path=alpha.txt')
        self.assertEqual((status, headers['Content-Type'], data), (200, 'text/plain; charset=utf-8', b'hi there'))
        status, headers, data = self.request('api/file?path=pic.png')
        self.assertEqual((status, headers['Content-Type'], data), (200, 'image/png', b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(self.request('api/file?path=tool.exe')[0], 415)
        self.assertEqual(self.request('api/file?path=missing.txt')[0], 404)
        self.assertEqual(self.request('api/file?path=../config/ui.defaults.json')[0], 404)

    # ---- 14
    def test_models(self):
        self.assertEqual(self.get_json('api/models')[1], {'models': [{'name': 'tz-agent:latest', 'size': 1234},
                                                                     {'name': 'gemma3:1b', 'size': 99}], 'vram_total': None})
        self.agent.fail_api = True
        self.assertEqual(self.get_json('api/models')[1], {'models': [], 'vram_total': None})

    # ---- 15
    def test_open_mode(self):
        self.assertEqual(open_mode(self.root), 'ask')
        self.assertEqual(set_open_mode('always', self.root), 'always')
        self.assertEqual(open_mode(self.root), 'always')
        with self.assertRaises(ValueError): set_open_mode('later', self.root)
        self.assertEqual(open_mode(self.root), 'always')

    # ---- 16
    def test_static_asset_serving(self):
        ui = self.root / 'ui'; ui.mkdir(); (ui / 'icons').mkdir()
        (ui / 'index.html').write_text('<h1>real</h1>', encoding='utf-8')
        (ui / 'desktop.js').write_text('let x = 1;', encoding='utf-8')
        (ui / 'icons' / 'tz.svg').write_text('<svg/>', encoding='utf-8')
        status, headers, data = self.request('ui/')
        self.assertEqual((status, data), (200, b'<h1>real</h1>')); self.assertIn('Content-Security-Policy', headers)
        status, headers, data = self.request('ui/desktop.js')
        self.assertEqual(status, 200); self.assertIn('javascript', headers['Content-Type'])
        self.assertNotIn('Content-Security-Policy', headers)
        self.assertEqual(self.request('ui/icons/tz.svg')[1]['Content-Type'], 'image/svg+xml')
        self.assertEqual(self.request('ui/missing.css')[0], 404)


if __name__ == '__main__':
    unittest.main()
