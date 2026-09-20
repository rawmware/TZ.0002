"""Quiet terminal chrome. Telemetry never owns the conversation or model loop."""
import contextlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
UNAVAILABLE = 'unavailable'


def helper(argv, timeout=2.0):
    """Run a local helper command windowlessly. Returns stdout, or None on any failure."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                creationflags=NO_WINDOW)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def gigabytes(value):
    return f'{value / 2**30:.1f} GB'


class Hardware:
    """Live utilization on a background thread, plus a one-shot static inventory."""

    def __init__(self, agent=None):
        self.agent = agent
        self.readings = 'CPU --  |  RAM --  |  GPU --  |  VRAM --'
        self.stop = threading.Event()
        self.thread = None
        self.inventory = None
        self.vram = None
        self.vram_known = False

    def vram_total(self):
        """Bytes of VRAM on GPU0 via nvidia-smi, sampled once. None without a working NVIDIA GPU."""
        if not self.vram_known:
            self.vram_known = True
            out = helper(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], timeout=4)
            first = (out or '').strip().splitlines()[:1]
            try: self.vram = int(float(first[0].strip().split(',')[0]) * 1024 * 1024) if first else None
            except ValueError: self.vram = None
        return self.vram

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            import psutil
        except ImportError:
            self.readings = 'psutil not installed - run: pip install -r requirements.txt'
            return
        gpu_command = shutil.which('nvidia-smi')
        psutil.cpu_percent()
        while not self.stop.wait(1):
            try:
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_percent()
                def bar(pct):
                    count = max(0, min(8, round(pct / 12.5)))
                    return '[' + '|' * count + '.' * (8 - count) + ']'
                parts = [f'CPU {bar(cpu)} {cpu:.0f}%',
                         f'RAM {mem.used / 2**30:.1f}/{mem.total / 2**30:.1f} GB']
                gpu = 'GPU n/a  |  VRAM n/a'
                if gpu_command:
                    result = subprocess.run([gpu_command,
                        '--query-gpu=utilization.gpu,memory.used,memory.total',
                        '--format=csv,noheader,nounits'], capture_output=True, text=True,
                        timeout=0.8, creationflags=NO_WINDOW)
                    rows = []
                    for i, row in enumerate(result.stdout.strip().splitlines()):
                        use, used, total = [float(v.strip()) for v in row.split(',')]
                        rows.append(f'GPU{i} {bar(use)} {use:.0f}%  |  VRAM {used / 1024:.1f}/{total / 1024:.1f} GB')
                    if result.returncode == 0 and rows: gpu = '  |  '.join(rows)
                self.readings = '  |  '.join(parts) + '  |  ' + gpu
            except (OSError, ValueError, subprocess.TimeoutExpired):
                # Never present stale GPU values as a fresh reading.
                self.readings = '  |  '.join(parts) + '  |  GPU n/a  |  VRAM n/a' if 'parts' in locals() else 'Hardware readings unavailable'

    # ---------------------------------------------------------------- inventory

    def specs(self, refresh=False):
        """Static machine inventory as (label, value) rows. Sampled once, never polled."""
        if self.inventory is None or refresh:
            self.inventory = self.collect()
        return self.inventory

    def collect(self):
        try:
            import psutil
        except ImportError:
            psutil = None
        rows = [('CPU', self.cpu(psutil)),
                ('Memory', gigabytes(psutil.virtual_memory().total) + ' total' if psutil
                 else 'psutil not installed - run: pip install -r requirements.txt')]
        rows.extend(self.graphics())
        rows.append(('OS', platform.platform()))
        rows.append(('Python', sys.version.split()[0] + f' ({platform.machine()})'))
        rows.append(('Disk', self.disk()))
        rows.extend(self.runtime())
        return rows

    def cpu(self, psutil):
        name = (platform.processor() or '').strip()
        if os.name == 'nt':
            # platform.processor() on Windows is a family/stepping string, not a model name.
            found = self.windows_query('Win32_Processor', 'Name')
            if found: name = str(found[0].get('Name', '')).strip() or name
        name = name or platform.machine() or 'unknown CPU'
        if not psutil:
            return name + ' - core count needs psutil'
        cores, threads = psutil.cpu_count(logical=False), psutil.cpu_count()
        detail = f'{cores or "?"} cores / {threads or "?"} threads'
        try:
            freq = psutil.cpu_freq()
        except (OSError, NotImplementedError, AttributeError):
            freq = None
        if freq and freq.max: detail += f' @ {freq.max / 1000:.2f} GHz'
        elif freq and freq.current: detail += f' @ {freq.current / 1000:.2f} GHz (current)'
        return f'{name}  -  {detail}'

    def graphics(self):
        """GPU name and total VRAM. nvidia-smi when present, otherwise an honest name-only row."""
        command = shutil.which('nvidia-smi')
        if command:
            out = helper([command, '--query-gpu=name,memory.total,driver_version',
                          '--format=csv,noheader,nounits'], timeout=4)
            rows = []
            for i, line in enumerate((out or '').strip().splitlines()):
                fields = [f.strip() for f in line.split(',')]
                if len(fields) < 3: continue
                name, total, driver = fields[0], fields[1], fields[2]
                try: vram = f'{float(total) / 1024:.1f} GB VRAM'
                except ValueError: vram = 'VRAM ' + UNAVAILABLE
                rows.append((f'GPU{i}', f'{name}  -  {vram}  -  driver {driver}'))
            if rows: return rows
        names = [str(entry.get('Name', '')).strip()
                 for entry in self.windows_query('Win32_VideoController', 'Name')]
        names = [n for n in names if n]
        if names:
            return [(f'GPU{i}', f'{n}  -  utilization not exposed (nvidia-smi only)')
                    for i, n in enumerate(names)]
        return [('GPU', 'not detected - utilization is read through nvidia-smi only')]

    def disk(self):
        target = getattr(self.agent, 'workspace', None) or os.getcwd()
        try:
            usage = shutil.disk_usage(str(target))
        except OSError:
            return UNAVAILABLE
        return f'{gigabytes(usage.free)} free of {gigabytes(usage.total)} on {self.drive(target)}'

    @staticmethod
    def drive(target):
        drive = os.path.splitdrive(str(target))[0]
        return drive or '/'

    def runtime(self):
        """Ollama endpoint, version, loaded model and where inference actually runs."""
        agent = self.agent
        if agent is None: return []
        rows = []
        version = self.ollama('/api/version')
        label = str(getattr(agent, 'base_url', '')) or UNAVAILABLE
        if version and version.get('version'): label = f'v{version["version"]}  -  {label}'
        else: label += '  -  version ' + UNAVAILABLE + ' (is Ollama running?)'
        rows.append(('Ollama', label))
        rows.append(('Model', str(getattr(agent, 'model_description', None) or getattr(agent, 'model', '?'))))
        rows.append(('Inference', self.device()))
        return rows

    def device(self):
        loaded = self.ollama('/api/ps')
        if not loaded: return UNAVAILABLE + ' - no model loaded yet (ask something first)'
        models = loaded.get('models') or []
        target = str(getattr(self.agent, 'model', ''))
        entry = next((m for m in models if m.get('name') == target or m.get('model') == target),
                     models[0] if models else None)
        if not entry: return 'no model resident - loads on the next request'
        total, vram = entry.get('size') or 0, entry.get('size_vram') or 0
        if not total: return UNAVAILABLE
        if vram <= 0: return f'CPU  -  {gigabytes(total)} resident, 0 GB on GPU'
        if vram >= total * 0.98: return f'GPU  -  {gigabytes(vram)} of {gigabytes(total)} in VRAM'
        return f'GPU + CPU split  -  {gigabytes(vram)} of {gigabytes(total)} in VRAM'

    def ollama(self, path):
        """Read-only loopback probe. Returns parsed JSON or None; never raises."""
        import urllib.parse
        import urllib.request
        base = str(getattr(self.agent, 'base_url', '') or '')
        parts = urllib.parse.urlsplit(base)
        if parts.scheme != 'http' or parts.hostname not in ('localhost', '127.0.0.1', '::1'):
            return None
        try:
            with urllib.request.urlopen(base + path, timeout=2) as response:
                return json.loads(response.read().decode('utf-8', 'replace'))
        except Exception:
            return None

    @staticmethod
    def windows_query(class_name, *properties):
        """CIM lookup so non-NVIDIA machines still get real names. Empty list off Windows."""
        if os.name != 'nt': return []
        out = helper(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                      f'Get-CimInstance {class_name} | Select-Object -Property '
                      f'{",".join(properties)} | ConvertTo-Json -Compress'], timeout=8)
        if not out or not out.strip(): return []
        try:
            data = json.loads(out)
        except ValueError:
            return []
        if isinstance(data, dict): return [data]
        return [item for item in data if isinstance(item, dict)]

    def close(self):
        self.stop.set()
        if self.thread: self.thread.join(timeout=2)


class Terminal:
    def __init__(self, agent):
        self.agent = agent
        self.hardware = Hardware(agent)
        self.enabled = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
        self.console = self.session = None
        self.stream_buffer = ''
        self.live = None
        self.verbose = True
        self.reply_open = False
        self.reply_title = None
        self.note = None
        self.code_lines = None
        self.code_language = None
        # Re-entrant: emit -> commit_lines -> print_line all take it. A UI worker thread may print
        # while the main thread sits at the prompt.
        self.lock = threading.RLock()
        self.turn_active = False
        self.interrupted = False
        if self.enabled:
            try:
                from rich.console import Console
                from prompt_toolkit import PromptSession
                from prompt_toolkit.key_binding import KeyBindings
                from prompt_toolkit.styles import Style
                self.console = Console(highlight=False)
                keys = KeyBindings()

                @keys.add('enter')
                def submit(event): event.current_buffer.validate_and_handle()

                @keys.add('escape', 'enter')
                @keys.add('c-j')
                def newline(event): event.current_buffer.insert_text('\n')

                # multiline + wrap_lines is what keeps a long prompt visible: it grows
                # downward instead of scrolling the start of the sentence off the left.
                self.session = PromptSession(multiline=True, wrap_lines=True,
                    erase_when_done=True, show_frame=True, reserve_space_for_menu=0,
                    key_bindings=keys,
                    prompt_continuation=lambda width, line_number, is_soft_wrap: ' ' * width,
                    style=Style.from_dict({'bottom-toolbar': 'fg:ansicyan bg:default', 'frame.border': 'fg:ansibrightblack'}))
            except ImportError:
                self.enabled = False
        if self.enabled: self.hardware.start()

    # ------------------------------------------------------------------ output

    def measure(self):
        """Cap the text column at a readable measure even on very wide terminals."""
        return min(100, max(20, self.console.width))

    def emit(self, value='', end='\n', flush=False):
        with self.lock: self._emit(value, end, flush)

    def _emit(self, value, end, flush):
        from app.tz_agent import clean
        value = clean(value)
        if not self.enabled:
            print(value, end=end, flush=flush)
            return
        tag = end != '' and value.startswith(('[route]', '[model]', '[usage]', '[tool]',
                                              '[waiting]', '[OpenCode]'))
        if tag and not self.verbose: return
        if self.live is not None:
            if end == '':
                self.stream_buffer += value
                self.commit_lines()
                return
            # A status line mid-turn: settle the streamed text before it interleaves.
            self.flush_stream()
            self.close_reply()
            if not value: return
        style = None
        if end != '':
            if value.startswith(('[route]', '[model]', '[OpenCode]')): style = 'cyan'
            elif value.startswith('[usage]'): style = 'green'
            elif value.startswith(('[incomplete]', '[tool error]')): style = 'yellow'
            elif value.startswith(('[tool]', '[waiting]')): style = 'dim'
        self.console.print(value, end=end, style=style, markup=False, highlight=False)

    # --------------------------------------------------------- streamed replies

    def commit_lines(self):
        """Print whole lines as they arrive so they settle into real scrollback."""
        while '\n' in self.stream_buffer:
            line, self.stream_buffer = self.stream_buffer.split('\n', 1)
            self.print_line(line)

    def flush_stream(self):
        if self.stream_buffer:
            line, self.stream_buffer = self.stream_buffer, ''
            self.print_line(line)

    def print_line(self, line):
        with self.lock: self._print_line(line)

    def _print_line(self, line):
        from rich.text import Text
        self.open_reply()
        fence = line.lstrip()
        if fence.startswith('```'):
            if self.code_lines is None:
                self.code_lines, self.code_language = [], fence[3:].strip().split()[:1]
                self.code_language = self.code_language[0] if self.code_language else 'text'
            else:
                self.print_code()
            return
        if self.code_lines is not None:
            self.code_lines.append(line)
            return
        style = 'bold' if fence.startswith('#') else None
        self.console.print(Text(line), style=style, markup=False, highlight=False,
                           width=self.measure())

    def print_code(self):
        """A finished fenced block is highlighted once, in place. Nothing above it redraws."""
        with self.lock: self._print_code()

    def _print_code(self):
        lines, language = self.code_lines or [], self.code_language or 'text'
        self.code_lines = self.code_language = None
        if not lines: return
        from rich.panel import Panel
        from rich.text import Text
        body = Text('\n'.join(lines))
        try:
            from rich.syntax import Syntax
            body = Syntax('\n'.join(lines), language, theme='ansi_dark', word_wrap=True,
                          background_color='default')
        except Exception:
            pass
        self.console.print(Panel(body, border_style='dim', padding=(0, 1),
                                 title=language, title_align='left'), width=self.measure())

    def open_reply(self):
        with self.lock:
            if self.reply_open: return
            self.reply_open = True
            from app.tz_agent import clean
            self.console.print()
            self.console.rule(self.reply_title or f'AI  ·  {clean(self.agent.model)}', align='left', style='green')

    def close_reply(self, note=''):
        with self.lock:
            if self.code_lines is not None: self.print_code()
            if not self.reply_open: return
            self.reply_open = False
            self.console.rule(note, align='left', style='yellow' if note else 'green')
            self.console.print()

    # ------------------------------------------------------------------ panels

    def header(self):
        from app.tz_agent import clean
        text = (f'{clean(self.agent.label)}  |  LOCAL AGENT  |  {self.agent.routing.upper()}\n'
                f'Model: {clean(self.agent.model)}\n{clean(self.agent.workspace)}\n'
                '/help  commands   /specs  this machine   /status  diagnostics   Ctrl+C  cancel')
        if self.enabled:
            from rich.panel import Panel
            from rich.text import Text
            styled = Text(text)
            styled.stylize('cyan', 0, len(clean(self.agent.label)))
            path = clean(self.agent.workspace)
            start = text.index(path)
            colors = ['white', 'red', 'white', 'dark_orange', 'yellow', 'green', 'blue']
            import re
            for i, match in enumerate(re.finditer(r'[^\\/]+', path)):
                styled.stylize(colors[min(i, len(colors) - 1)], start + match.start(), start + match.end())
            self.console.print(Panel(styled, border_style='cyan', padding=(1, 2)))
        else: self.emit(text)

    def specs(self, refresh=False):
        """The spec sheet: what this machine actually is, gathered once."""
        rows = self.hardware.specs(refresh=refresh)
        if not self.enabled:
            self.emit('\n'.join(f'{label}: {value}' for label, value in rows))
            return
        from rich.panel import Panel
        from rich.table import Table
        table = Table.grid(padding=(0, 3))
        table.add_column(justify='right', style='dim', no_wrap=True)
        table.add_column(style='white', overflow='fold')
        for label, value in rows: table.add_row(label, str(value))
        self.console.print(Panel(table, title='This machine', title_align='left',
                                 border_style='cyan', padding=(1, 2)))

    def help(self, text):
        if not self.enabled:
            self.emit(text)
            return
        import re
        from rich.panel import Panel
        from rich.table import Table
        table = Table.grid(padding=(0, 3))
        table.add_column(style='cyan', no_wrap=True)
        table.add_column(style='white', overflow='fold')
        lines = text.splitlines()
        title = lines[0] if lines else 'TZ'
        for line in lines[1:]:
            if not line.strip(): continue
            parts = re.split(r'\s{2,}', line.strip(), maxsplit=1)
            table.add_row(parts[0], parts[1] if len(parts) > 1 else '')
        self.console.print(Panel(table, title=title, title_align='left',
                                 border_style='cyan', padding=(1, 2)))

    def table(self, title, columns, rows):
        """A small bordered table, e.g. a team plan. Plain columns when redirected."""
        if not self.enabled:
            widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(columns)]
            self.emit(title)
            self.emit('  '.join(str(c).ljust(widths[i]) for i, c in enumerate(columns)))
            for row in rows: self.emit('  '.join(str(v).ljust(widths[i]) for i, v in enumerate(row)))
            return
        from rich.table import Table
        from app.tz_agent import clean
        grid = Table(title=title, title_justify='left', border_style='cyan', header_style='bold cyan',
                     padding=(0, 1), show_edge=True)
        for column in columns: grid.add_column(str(column), overflow='fold')
        for row in rows: grid.add_row(*(clean(v) for v in row))
        self.console.print()
        self.console.print(grid, width=self.measure())

    # ------------------------------------------------------------------- input

    def status_line(self):
        """Model, route, workspace and session: the persistent answer to "what am I running"."""
        from app.tz_agent import clean
        return (f'{clean(self.agent.model)} · {self.agent.routing.upper()} · '
                f'{os.path.basename(str(self.agent.workspace)) or str(self.agent.workspace)} · {self.agent.id}')

    def toolbar(self):
        """One row, always. The second GPU line would push the input area off short windows."""
        text = self.status_line() + '  |  ' + self.hardware.readings.replace('\n', '  ')
        try:
            typed = len(self.session.default_buffer.text)
        except Exception:
            typed = 0
        if typed > 120: text += f'  |  {typed} chars'
        try:
            width = self.console.width
        except Exception:
            width = 0
        if width and len(text) > width:
            text = text[:max(0, width - 1)] + '…'
        return text

    def read(self):
        if not self.enabled: return input('Me > ')
        from prompt_toolkit.formatted_text import ANSI
        color = '' if 'NO_COLOR' in os.environ else '\x1b[36m'
        reset = '' if 'NO_COLOR' in os.environ else '\x1b[0m'
        try:
            # Lines printed by another thread (a UI-driven turn) land above the input box instead of inside it.
            # Rich resolves sys.stdout at print time, so its output goes through the same proxy.
            from prompt_toolkit.application.current import create_app_session
            from prompt_toolkit.patch_stdout import patch_stdout
            # The proxy must write through the prompt's own output object, not a second console handle.
            with create_app_session(input=self.session.input, output=self.session.output), patch_stdout(raw=True):
                text = self.session.prompt(ANSI(color + 'Me > ' + reset),
                    bottom_toolbar=self.toolbar, refresh_interval=1)
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception:
            # A terminal capability failure must not become a busy error loop.
            self.enabled = False
            self.hardware.close()
            return input('Me > ')
        if text.strip():
            from rich.panel import Panel
            from rich.text import Text
            from app.tz_agent import clean
            self.console.print(Panel(Text(clean(text)), title='Me', title_align='left',
                                     border_style='dim', padding=(0, 1), width=self.measure()))
        return text

    def yes_no(self, question, default=False, hint=''):
        """One Y/N line: '<question> (Y/N)  [Enter = N]'. Empty answer means the default.

        Not interactive (no TTY, tests, --prompt): returns the default without touching stdin.
        `hint` is shown dimmed under the line while it waits.
        """
        if not self.enabled: return default
        label = f'{question} (Y/N)  [Enter = {"Y" if default else "N"}] '
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.styles import Style
            session = PromptSession(style=Style.from_dict({'bottom-toolbar': 'noreverse fg:ansibrightblack bg:default'}))
            for _ in range(3):
                answer = session.prompt(label, bottom_toolbar=(hint or None)).strip().lower()
                if answer in ('y', 'yes'): return True
                if answer in ('n', 'no'): return False
                if not answer: return default
        except (EOFError, KeyboardInterrupt):
            return default
        except Exception:
            # A prompt failure must never block start-up.
            return default
        return default

    # ---------------------------------------------------------------- activity

    @contextlib.contextmanager
    def activity(self):
        """Marks one turn as running. `interrupted` stays set after a Ctrl+C so the loop can report it honestly."""
        self.turn_active, self.interrupted = True, False
        try:
            with (self.live_panel() if self.enabled else contextlib.nullcontext()): yield
        except KeyboardInterrupt:
            self.interrupted = True
            raise
        finally:
            self.turn_active = False

    @contextlib.contextmanager
    def live_panel(self):
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        started = time.monotonic()
        def render():
            # Fixed height, always. The reply prints above this block, never inside it.
            note = f'  ·  {self.note}' if self.note else ''
            return Panel(Text(f'ACTIVE  ·  {time.monotonic() - started:.0f}s  ·  '
                              f'{self.agent.routing.upper()}{note}  ·  Ctrl+C cancels\n'
                              + self.hardware.readings, style='cyan'), border_style='dim cyan')
        note = ''
        with Live(console=self.console, get_renderable=render, refresh_per_second=2,
                  transient=True) as live:
            self.live = live
            try:
                yield
            except KeyboardInterrupt:
                note = '- canceled, unverified'
                raise
            except Exception:
                note = '- incomplete'
                raise
            finally:
                self.flush_stream()
                self.close_reply(note)
                self.live = None
                self.reply_title = self.note = None

    def close(self):
        self.hardware.close()
