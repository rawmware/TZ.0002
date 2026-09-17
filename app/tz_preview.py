"""Session-owned, loopback-only HTML preview with no external dependencies."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
import threading
from urllib.parse import quote, unquote, urlsplit
import uuid
import webbrowser


class Preview:
    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve()
        self.server = None
        self.opened = set()
        self.token = uuid.uuid4().hex
        self.live = True

    def start(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def do_GET(self):
                route = urlsplit(self.path)
                prefix = '/' + owner.token + '/'
                if not route.path.startswith(prefix):
                    self.send_error(404); return
                path = (owner.workspace / unquote(route.path[len(prefix):])).resolve()
                if not path.is_relative_to(owner.workspace) or not path.is_file():
                    self.send_error(404); return
                try:
                    data = path.read_bytes()
                    stamp = hashlib.sha256(data).hexdigest()
                    kind = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                    if route.query == 'tz_revision':
                        data, kind = stamp.encode(), 'text/plain'
                    elif path.suffix.lower() in ('.html', '.htm'):
                        script = """<script>(()=>{const revision='%s';setInterval(async()=>{
try{const u=new URL(location.href);u.search='tz_revision';
const r=await fetch(u,{cache:'no-store'});if(r.ok&&(await r.text())!==revision)location.reload();
}catch(e){}},800);})();</script>""" % stamp
                        data += script.encode()
                    self.send_response(200)
                    self.send_header('Content-Type', kind + ('; charset=utf-8' if kind.startswith('text/') else ''))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def open(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.workspace):
            raise ValueError('Preview must stay inside the workspace.')
        try:
            if not self.live: raise OSError('One-shot request: direct file preview; use interactive TZ for live reload.')
            if self.server is None: self.start()
            url = f'http://127.0.0.1:{self.server.server_port}/{self.token}/' + quote(path.relative_to(self.workspace).as_posix())
            if path not in self.opened:
                if not webbrowser.open(url): raise OSError('Browser did not accept preview URL')
                self.opened.add(path)
            return {'url': url, 'live_reload': True, 'note': 'Preview available while TZ is running; rendering not verified.'}
        except Exception as exc:
            url = path.as_uri()
            try: opened = webbrowser.open(url)
            except Exception: opened = False
            return {'url': url, 'live_reload': False, 'opened': opened, 'note': str(exc)}

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.opened.clear()
