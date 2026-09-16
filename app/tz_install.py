"""Per-user launch command registration. No PowerShell runtime dependency."""
import ctypes
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def settings(root=ROOT):
    path = Path(root) / 'config' / 'tz.local.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'passcode': 'TZ'}


def register(name, root=ROOT, desktop=False, bin_dir=None, update_path=True):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', name):
        raise ValueError('Use 1–32 letters, digits, hyphens or underscores, starting with a letter.')
    if name.lower() in {'con', 'prn', 'aux', 'nul', 'python', 'python3', 'py', 'cmd', 'powershell', 'pwsh', 'git', 'node', 'ollama', 'exit', 'cd', 'dir', 'ls', 'sh', 'bash'} or re.fullmatch(r'(?:com|lpt)[0-9]', name, re.I):
        raise ValueError('Choose a name that is not an existing system command.')
    root = Path(root).resolve()
    config = settings(root)
    folder = Path(bin_dir) if bin_dir else (Path(os.environ['LOCALAPPDATA']) / 'TZ' / 'bin' if os.name == 'nt' else Path.home() / '.local' / 'bin')
    suffix = '.cmd' if os.name == 'nt' else ''
    command = folder / (name + suffix)
    existing = shutil.which(name)
    if existing and Path(existing).resolve() not in (command.resolve(), (root / ('TZ.cmd' if os.name == 'nt' else 'tz')).resolve()):
        raise ValueError('Name is already used by ' + existing)
    folder.mkdir(parents=True, exist_ok=True)
    marker = 'TZ managed launcher'
    if command.exists() and marker not in command.read_text(encoding='utf-8', errors='replace'):
        # Only migrate this app's known historical shims.
        previous = command.read_text(encoding='utf-8', errors='replace')
        if str(root).lower() not in previous.lower(): raise ValueError('Existing launcher belongs to another installation: ' + str(command))
        backup = root / 'data' / 'launcher-backups'
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(command, backup / (str(time.time_ns()) + '-' + command.name))
    if os.name == 'nt':
        interpreter = sys.executable.replace('%', '%%')
        entry = str(root / 'tz.py').replace('%', '%%')
        content = '@echo off\r\nrem ' + marker + '\r\n"' + interpreter + '" "' + entry + '" %*\r\n'
    else:
        content = '#!/bin/sh\n# ' + marker + '\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(root / 'tz.py')) + ' "$@"\n'
    command.write_text(content, encoding='utf-8', newline='')
    if os.name != 'nt': command.chmod(0o755)
    if update_path:
        if os.name == 'nt':
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
                try: old, kind = winreg.QueryValueEx(key, 'Path')
                except FileNotFoundError: old, kind = '', winreg.REG_EXPAND_SZ
                if str(folder).lower() not in [x.lower().rstrip('\\') for x in old.split(';')]:
                    winreg.SetValueEx(key, 'Path', 0, kind, str(folder) + ';' + old)
            # Notify Explorer; new terminals pick up this user's PATH.
            result = ctypes.c_size_t()
            ctypes.windll.user32.SendMessageTimeoutW(65535, 0x1A, 0, 'Environment', 2, 1000, ctypes.byref(result))
        os.environ['PATH'] = str(folder) + os.pathsep + os.environ.get('PATH', '')
    config['passcode'] = name
    config['launcher'] = str(command)
    (root / 'config').mkdir(exist_ok=True)
    (root / 'config' / 'tz.local.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    if desktop and os.name == 'nt': install_shortcut(root)
    return command


def install_shortcut(root=ROOT):
    # Windows Script Host is used only by installation; the app itself runs Python.
    root = Path(root).resolve()
    backup = root / 'data' / 'launcher-backups'
    backup.mkdir(parents=True, exist_ok=True)
    def vb(s): return '"' + str(s).replace('"', '""') + '"'
    script = '\n'.join([
        'Set shell = CreateObject("WScript.Shell")',
        'Set fs = CreateObject("Scripting.FileSystemObject")',
        'For Each folder In Array(shell.SpecialFolders("Desktop"), shell.SpecialFolders("Programs"))',
        '  old = folder & "\\Roman TZ.lnk"',
        '  If fs.FileExists(old) Then',
        '    Set link = shell.CreateShortcut(old)',
        '    If InStr(1, link.TargetPath & " " & link.Arguments, ' + vb(root) + ', 1) > 0 Then',
        '      fs.MoveFile old, ' + vb(str(backup) + '\\' + str(time.time_ns()) + '-') + ' & fs.GetFileName(folder) & "-Roman TZ.lnk"',
        '    End If',
        '  End If',
        '  Set link = shell.CreateShortcut(folder & "\\TZ.lnk")',
        '  link.TargetPath = ' + vb(sys.executable),
        '  link.Arguments = ' + vb('"' + str(root / 'tz.py') + '"'),
        '  link.WorkingDirectory = ' + vb(root),
        '  link.Description = "TZ local task agent"',
        '  link.Save',
        'Next',
    ])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'shortcut.vbs'
        path.write_text(script, encoding='utf-16')
        subprocess.run(['cscript.exe', '//NoLogo', str(path)], check=True, capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Install TZ launch commands for this user.')
    parser.add_argument('--name', default='TZ')
    parser.add_argument('--desktop', action='store_true')
    parser.add_argument('--setup-model', action='store_true', help='Install a 2.5 GB local instruction model for TZ and OpenCode.')
    args = parser.parse_args()
    if args.setup_model: setup_model()
    for name in ('tz', 'roman', 'rom'):
        register(name)
    command = register(args.name, desktop=args.desktop)
    print('Registered:', command)
    print('Open a new terminal and type', args.name)
    if os.name != 'nt': print('Ensure ~/.local/bin is on your PATH, or use the full command path above.')
    return 0


def setup_model():
    from app.tz_agent import Agent
    agent = Agent()
    available = [m['name'] for m in agent.api('/api/tags')['models']]
    base = 'qwen3:4b-instruct-2507-q4_K_M'
    if base not in available:
        subprocess.run(['ollama', 'pull', base], check=True)
    result = agent.api('/api/create', {'model': 'tz-agent:latest', 'from': base,
                                      'parameters': {'num_ctx': 16384}, 'stream': False})
    if result.get('status') != 'success': raise RuntimeError('Agent model setup did not complete: ' + str(result))
    print('Ready: tz-agent:latest (local Qwen3 4B Instruct; shared weights, 16K context).')
