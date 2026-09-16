# TZ - local task agent

TZ reads files, fetches web pages, searches, writes and verifies files, runs explicit commands, and uses **OpenCode + local Ollama** for coding tasks. The default runtime is Python 3.10+, with no PowerShell dependency.

## Install on another machine

Install Python 3.10+, Node.js/npm, Git and Ollama; start Ollama. Then:

```text
git clone https://github.com/rawmware/TZ.0002.git
cd TZ.0002
python -m pip install -r requirements.txt
npm i -g opencode-ai
python install.py --setup-model --desktop
python tz.py --doctor
```

On macOS/Linux use `python3`; `--desktop` only creates a shortcut on Windows. Add `~/.local/bin` to PATH for installed Unix aliases. Or launch directly with `python3 tz.py` / `sh tz`.

The local model is Qwen3 4B Instruct (~2.5 GB), registered as `tz-agent:latest` with 16K context. Model quality and speed depend on hardware. No cloud model/API key is required by this default configuration. OpenCode may download provider dependencies on first use.

## Use

Open the single **TZ** desktop shortcut, run `TZ.cmd`, or type `tz`, `roman`, or `rom` after installation.

```text
read "D:/downloads/AGENTS.md"
/read "D:/downloads/paper.pdf" 0 6000
/fetch https://example.com
/search projects using codex
Create an HTML file with a heading Hello Roman and verify it.
/opencode Build a simple webpage in this workspace and read it back.
/opencode
/passcode nova
```

`/opencode` alone opens the full OpenCode terminal UI. Coding requests automatically use OpenCode when installed. Follow-up coding tasks reuse the OpenCode session. `/passcode nova` changes the prompt **and registers `nova` as a launch command**. `tz` and previous aliases remain available. This name is not a password.

Direct tools run without asking a model for permission. TZ's built-in writes verify the bytes and ask before replacing existing files, with backups. OpenCode is permitted to edit workspace files and shows completed/failed tool events. Its shell commands require interactive approval; use `/opencode` for those workflows. Explicit `/run ["python", "script.py"]` runs that program without assuming a shell.

`/help`, `/tools`, `/status`, `/models`, `/use MODEL`, `/clear`, `/exit` are available. `Ctrl+C` cancels model generation; incomplete output is never labeled verified. `python tz.py --prompt "REQUEST"` runs one task for scripts. `--workspace PATH` selects an existing project directory. `--resume SESSION_ID` resumes a local session.

## Verification and portability

```text
python -m unittest discover -s tests -p test_tz.py -v
```

Tests cover original file-request routing, real launch aliases, file verification, command execution, OpenCode routing and model timeout/truncation. CI runs the portable tests on Windows, Linux and macOS. Desktop live tests used Windows, local Ollama and OpenCode 1.18.31; see the build notes for evidence and limits.

- [Laptop setup and sync boundaries](docs/TZ-LAPTOP-SETUP.md)
- [Boris Cherny research, architecture decisions and fixes](docs/TZ-BORIS-AND-BUILD-NOTES.md)

The previous PowerShell application remains at `Start-RAWM.ps1` for legacy desktop-specific features. Older documents and PowerShell tests describe that runtime. Git synchronizes application code, not private conversations, credentials, model weights, or machine-specific launcher paths.
