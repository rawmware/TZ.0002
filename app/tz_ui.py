"""Loopback desktop UI server: static page, JSON API and SSE fan-out around one Agent."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import queue
import re
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.4'
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; connect-src 'self'"
UI_KEYS = ('open', 'wallpaper', 'wallpaper_image', 'chime', 'presets', 'removed')
OPEN_MODES = ('ask', 'always', 'never')
DEFAULTS = {'open': 'ask', 'wallpaper': '#008080', 'wallpaper_image': '', 'chime': False, 'removed': [], 'presets': []}
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
               '.bmp': 'image/bmp', '.webp': 'image/webp', '.svg': 'image/svg+xml'}
TEXT_SUFFIXES = {'', '.txt', '.md', '.py', '.js', '.css', '.html', '.htm', '.json', '.jsonl', '.csv', '.log', '.ps1',
                 '.cmd', '.bat', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.xml', '.sh', '.ts', '.rst'}
PLACEHOLDER = ('<!doctype html><html><head><meta charset="utf-8"><title>TZ desktop</title></head>'
               '<body style="background:#008080;color:#fff;font-family:Tahoma,sans-serif;padding:24px">'
               '<h1>TZ desktop</h1><p>TZ desktop — front end not installed (ui/index.html is missing).</p>'
               '</body></html>')


# ---------------------------------------------------------------- config layers

def read_json(path, fallback):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def local_settings(root):
    data = read_json(Path(root) / 'config' / 'tz.local.json', {})
    return data if isinstance(data, dict) else {}


def ui_config(root=ROOT):
    root = Path(root)
    defaults = dict(DEFAULTS)
    defaults.update(read_json(root / 'config' / 'ui.defaults.json', {}))
    local = local_settings(root).get('ui', {})
    local = local if isinstance(local, dict) else {}
    config = {key: local.get(key, defaults[key]) for key in UI_KEYS if key != 'presets'}
    presets = {p['id']: dict(p) for p in defaults.get('presets', []) if isinstance(p, dict) and 'id' in p}
    for p in local.get('presets', []) if isinstance(local.get('presets'), list) else []:
        if isinstance(p, dict) and 'id' in p: presets[p['id']] = dict(p)
    removed = set(config['removed']) if isinstance(config['removed'], list) else set()
    config['presets'] = [p for p in presets.values() if p['id'] not in removed]
    return config


def validate(key, value):
    if key == 'open':
        if value not in OPEN_MODES: raise ValueError('open must be one of ask, always, never')
    elif key == 'wallpaper':
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value): raise ValueError('wallpaper must be a #RRGGBB color')
    elif key == 'wallpaper_image':
        if not isinstance(value, str): raise ValueError('wallpaper_image must be a string')
    elif key == 'chime':
        if not isinstance(value, bool): raise ValueError('chime must be true or false')
    elif key == 'removed':
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value): raise ValueError('removed must be a list of preset ids')
    elif key == 'presets':
        if not isinstance(value, list): raise ValueError('presets must be a list')
        clean = []
        for p in value:
            if not isinstance(p, dict): raise ValueError('Each preset must be an object')
            pid, name, phrase = p.get('id'), p.get('name'), p.get('phrase')
            mode, icon = p.get('mode'), p.get('icon', 'preset')
            if not isinstance(pid, str) or not re.fullmatch(r'[a-z0-9-]{1,40}', pid): raise ValueError('Preset id must be 1-40 lowercase letters, digits or hyphens')
            if not isinstance(name, str) or not 1 <= len(name) <= 40: raise ValueError('Preset name must be 1-40 characters')
            if not isinstance(phrase, str) or not 1 <= len(phrase) <= 200: raise ValueError('Preset phrase must be 1-200 characters')
            if mode not in ('ask', 'browser'): raise ValueError('Preset mode must be ask or browser')
            if not isinstance(icon, str): raise ValueError('Preset icon must be a string')
            clean.append({'id': pid, 'name': name, 'phrase': phrase, 'mode': mode, 'icon': icon})
        return clean
    return value


def write_ui_config(changes, root=ROOT):
    if not isinstance(changes, dict): raise ValueError('UI settings must be an object')
    for key in changes:
        if key not in UI_KEYS: raise ValueError('Unknown UI setting: ' + str(key))
    clean = {key: validate(key, value) for key, value in changes.items()}
    root = Path(root)
    path = root / 'config' / 'tz.local.json'
    data = local_settings(root)
    ui = data.get('ui') if isinstance(data.get('ui'), dict) else {}
    ui.update(clean)
    data['ui'] = ui
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return ui_config(root)


def open_mode(root=ROOT):
    return ui_config(root)['open']


def set_open_mode(mode, root=ROOT):
    return write_ui_config({'open': mode}, root)['open']


# ---------------------------------------------------------------- desktop

class Desktop:
    def __init__(self, agent, terminal=None, root=ROOT):
        self.agent, self.terminal, self.root = agent, terminal, Path(root)
        self.token = uuid.uuid4().hex
        self.server = None
        self.clients, self.clients_lock = set(), threading.Lock()
        self.pending = {}
        self.original_emit = self.original_command = self.original_confirm = None
        self.status_thread = None
        self.stop = threading.Event()
        self.local = threading.local()

    # ---- lifecycle
    def open(self):
        if self.server is None:
            self.stop.clear()
            self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self))
            self.server.daemon_threads = True
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            self.hook()
            self.status_thread = threading.Thread(target=self.status_loop, daemon=True)
            self.status_thread.start()
        url = self.url()
        try: webbrowser.open(url)
        except Exception: pass
        return url

    def url(self):
        return f'http://127.0.0.1:{self.server.server_port}/{self.token}/ui/'

    def close(self):
        self.stop.set()
        self.unhook()
        with self.clients_lock:
            clients, self.clients = list(self.clients), set()
        for q in clients: q.put(None)
        if self.server is not None:
            self.server.shutdown(); self.server.server_close(); self.server = None

    # ---- hooks on the agent
    def hook(self):
        self.original_emit = self.agent.emit
        self.agent.emit = self.emit
        self.original_command = getattr(self.agent, 'command', None) or self.agent.turn
        self.agent.command = self.command

    def unhook(self):
        if self.original_emit is not None:
            self.agent.emit, self.original_emit = self.original_emit, None
        if self.original_command is not None:
            self.agent.command, self.original_command = self.original_command, None
        if self.original_confirm is not None:
            self.agent.confirm, self.original_confirm = self.original_confirm, None

    def emit(self, value='', end='\n', flush=False):
        self.original_emit(value, end=end, flush=flush)
        self.publish({'type': 'stream' if end == '' else 'line', 'text': str(value)})

    def command(self, text):
        self.publish({'type': 'turn_start', 'text': text, 'source': getattr(self.local, 'source', 'terminal')})
        try:
            result = self.original_command(text)
        except Exception as exc:
            self.publish({'type': 'turn_end', 'ok': False, 'error': str(exc)}); raise
        self.publish({'type': 'turn_end', 'ok': True})
        return result

    def confirm_bridge(self, question):
        cid = uuid.uuid4().hex
        slot = {'event': threading.Event(), 'answer': False}
        self.pending[cid] = slot
        try:
            self.publish({'type': 'confirm', 'id': cid, 'question': str(question)})
            slot['event'].wait(120)
            answer = bool(slot['answer']) if slot['event'].is_set() else False
        finally:
            self.pending.pop(cid, None)
        self.publish({'type': 'confirm_done', 'id': cid, 'answer': answer})
        return answer

    def answer(self, cid, value):
        slot = self.pending.get(cid)
        if slot is None: return False
        slot['answer'] = bool(value); slot['event'].set()
        return True

    def run_turn(self, text):
        """Worker for api/turn: UI-sourced, confirm bridged for the duration."""
        self.local.source = 'ui'
        original, bridge = self.agent.confirm, self.confirm_bridge
        self.original_confirm, self.agent.confirm = original, bridge
        try:
            self.agent.command(text)
        except Exception as exc:
            try: self.emit('[incomplete] ' + str(exc))
            except Exception: pass
        finally:
            if self.agent.confirm is bridge: self.agent.confirm = original
            self.original_confirm = None

    # ---- fan-out
    def subscribe(self):
        q = queue.Queue()
        with self.clients_lock: self.clients.add(q)
        return q

    def unsubscribe(self, q):
        with self.clients_lock: self.clients.discard(q)

    def publish(self, event):
        with self.clients_lock: clients = list(self.clients)
        for q in clients:
            if q.qsize() > 2000: self.unsubscribe(q); q.put(None)
            else: q.put(event)

    def busy(self):
        lock = getattr(self.agent, 'lock', None)
        return bool(lock.locked()) if lock is not None else False

    def readings(self):
        return getattr(getattr(self.terminal, 'hardware', None), 'readings', '') if self.terminal else ''

    def status_loop(self):
        while not self.stop.wait(1):
            self.publish({'type': 'status', 'readings': self.readings(), 'model': self.agent.model,
                          'routing': self.agent.routing, 'session_id': self.agent.id, 'busy': self.busy()})

    def state(self):
        specs = []
        if self.terminal is not None:
            try: specs = [list(row) for row in self.terminal.hardware.specs()]
            except Exception: specs = []
        a = self.agent
        return {'label': a.label, 'model': a.model, 'model_description': getattr(a, 'model_description', a.model),
                'task_model': a.task_model, 'routing': a.routing, 'session_id': a.id, 'workspace': str(a.workspace),
                'busy': self.busy(), 'specs': specs, 'readings': self.readings(), 'version': VERSION}

    def models(self):
        try:
            tags = self.agent.api('/api/tags').get('models', [])
            models = [{'name': m.get('name', ''), 'size': m.get('size', 0)} for m in tags]
            hardware = getattr(self.terminal, 'hardware', None)
            vram = hardware.vram_total() if hardware is not None and hasattr(hardware, 'vram_total') else None
            return {'models': models, 'vram_total': vram}
        except Exception:
            return {'models': [], 'vram_total': None}


# ---------------------------------------------------------------- HTTP

class Reply(Exception):
    def __init__(self, status, error): self.status, self.error = status, error


def make_handler(desktop):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_GET(self): self.route('GET')
        def do_POST(self): self.route('POST')
        def do_PUT(self): self.route('PUT')

        # ---- helpers
        def head(self, status, kind, length=None, html=False):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if html: self.send_header('Content-Security-Policy', CSP)
            if length is not None: self.send_header('Content-Length', str(length))
            self.end_headers()

        def send(self, status, data, kind, html=False):
            self.head(status, kind, len(data), html)
            self.wfile.write(data)

        def json(self, status, obj):
            self.send(status, json.dumps(obj).encode('utf-8'), 'application/json; charset=utf-8')

        def body(self):
            try: length = int(self.headers.get('Content-Length') or 0)
            except ValueError: raise Reply(400, 'Bad Content-Length')
            if length > 1_000_000: raise Reply(413, 'Body too large')
            raw = self.rfile.read(length) if length else b''
            if not raw: return {}
            try: data = json.loads(raw.decode('utf-8'))
            except ValueError: raise Reply(400, 'Body must be JSON')
            if not isinstance(data, dict): raise Reply(400, 'Body must be a JSON object')
            return data

        def query(self, route):
            return {k: v[-1] for k, v in parse_qs(route.query).items()}

        # ---- routing
        def route(self, method):
            route = urlsplit(self.path)
            prefix = '/' + desktop.token + '/'
            if not route.path.startswith(prefix):
                self.send_error(404); return
            rel = route.path[len(prefix):]
            try:
                if method == 'GET' and (rel == 'ui' or rel.startswith('ui/')): self.asset(rel[3:])
                elif rel == 'api/events' and method == 'GET': self.events()
                elif rel in API.get(method, {}): API[method][rel](self, route)
                else:
                    m = re.fullmatch(r'api/sessions/([a-zA-Z0-9-]+)(/resume)?', rel)
                    if m and method == 'GET' and not m.group(2): self.session(m.group(1))
                    elif m and method == 'POST' and m.group(2): self.resume(m.group(1))
                    else: raise Reply(404, 'Not found')
            except Reply as exc:
                self.json(exc.status, {'error': exc.error})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                try: self.json(500, {'error': str(exc)})
                except OSError: pass

        # ---- static
        def asset(self, rel):
            folder = (desktop.root / 'ui').resolve()
            rel = unquote(rel) or 'index.html'
            path = (folder / rel).resolve()
            if not path.is_relative_to(folder): raise Reply(404, 'Not found')
            if not path.is_file():
                if rel == 'index.html': self.send(200, PLACEHOLDER.encode('utf-8'), 'text/html; charset=utf-8', html=True); return
                raise Reply(404, 'Not found')
            kind = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            html = path.suffix.lower() in ('.html', '.htm')
            if kind.startswith('text/') or kind in ('application/javascript', 'application/json'): kind += '; charset=utf-8'
            self.send(200, path.read_bytes(), kind, html=html)

        # ---- SSE
        def events(self):
            q = desktop.subscribe()
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()
                self.push(dict(desktop.state(), type='hello'))
                while not desktop.stop.is_set():
                    try: event = q.get(timeout=15)
                    except queue.Empty:
                        self.wfile.write(b': keep-alive\n\n'); self.wfile.flush(); continue
                    if event is None: break
                    self.push(event)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                desktop.unsubscribe(q)

        def push(self, event):
            self.wfile.write(b'data: ' + json.dumps(event).encode('utf-8') + b'\n\n'); self.wfile.flush()

        # ---- API
        def state(self, route): self.json(200, desktop.state())

        def turn(self, route):
            text = self.body().get('text')
            if not isinstance(text, str) or not text.strip(): raise Reply(400, 'text is required')
            if desktop.busy(): raise Reply(409, 'busy')
            threading.Thread(target=desktop.run_turn, args=(text.strip(),), daemon=True).start()
            self.json(202, {'accepted': True})

        def confirm(self, route):
            data = self.body()
            if not desktop.answer(str(data.get('id', '')), data.get('answer', False)): raise Reply(404, 'No such confirm')
            self.json(200, {'ok': True})

        def sessions(self, route): self.json(200, desktop.agent.sessions())

        def session(self, sid):
            try: self.json(200, desktop.agent.session(desktop.agent.id if sid == 'current' else sid))
            except ValueError as exc: raise Reply(404, str(exc))

        def resume(self, sid):
            if desktop.busy(): raise Reply(409, 'busy')
            try: result = desktop.agent.resume(sid)
            except ValueError as exc: raise Reply(404, str(exc))
            desktop.publish({'type': 'session', 'id': desktop.agent.id})
            self.json(200, result)

        def new_session(self, route):
            if desktop.busy(): raise Reply(409, 'busy')
            result = desktop.agent.new_session()
            desktop.publish({'type': 'session', 'id': desktop.agent.id})
            self.json(200, result)

        def config_get(self, route): self.json(200, ui_config(desktop.root))

        def config_put(self, route):
            try: self.json(200, write_ui_config(self.body(), desktop.root))
            except ValueError as exc: raise Reply(400, str(exc))

        def models(self, route): self.json(200, desktop.models())

        def open_url(self, route):
            url = self.body().get('url')
            if not isinstance(url, str) or not re.match(r'https?://', url, re.I): raise Reply(400, 'Only http(s) URLs can be opened')
            try: self.json(200, desktop.agent.tool('open_target', {'target': url}, explicit=True))
            except (ValueError, RuntimeError) as exc: raise Reply(400, str(exc))

        def workspace_path(self, route):
            workspace = Path(desktop.agent.workspace).resolve()
            rel = unquote(self.query(route).get('path', '.')) or '.'
            path = (workspace / rel).resolve()
            if not path.is_relative_to(workspace) or not path.exists(): raise Reply(404, 'Not found')
            return workspace, path

        def files(self, route):
            workspace, path = self.workspace_path(route)
            if not path.is_dir(): raise Reply(404, 'Not a folder')
            entries = []
            for child in sorted(path.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
                try: entries.append({'name': child.name, 'dir': child.is_dir(), 'size': 0 if child.is_dir() else child.stat().st_size})
                except OSError: continue
                if len(entries) >= 500: break
            self.json(200, {'path': path.relative_to(workspace).as_posix(), 'entries': entries})

        def file(self, route):
            workspace, path = self.workspace_path(route)
            if not path.is_file(): raise Reply(404, 'Not a file')
            suffix = path.suffix.lower()
            if suffix in IMAGE_TYPES:
                self.send(200, path.read_bytes(), IMAGE_TYPES[suffix])
            elif suffix in TEXT_SUFFIXES:
                if path.stat().st_size > 1_000_000: raise Reply(415, 'Text file too large to show')
                self.send(200, path.read_bytes().decode('utf-8', errors='replace').encode('utf-8'), 'text/plain; charset=utf-8')
            else:
                raise Reply(415, 'Unsupported file type')

    API = {
        'GET': {'api/state': Handler.state, 'api/sessions': Handler.sessions,
                'api/sessions/current': lambda h, r: h.session('current'), 'api/config': Handler.config_get,
                'api/models': Handler.models, 'api/files': Handler.files, 'api/file': Handler.file},
        'POST': {'api/turn': Handler.turn, 'api/confirm': Handler.confirm, 'api/sessions/new': Handler.new_session,
                 'api/open': Handler.open_url},
        'PUT': {'api/config': Handler.config_put},
    }
    return Handler
