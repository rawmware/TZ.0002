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

## Terminal, routing and HTML previews

The interactive Python app uses a compact framed input, a separate **Me** identity,
your configured assistant name, cyan status accents, green token usage, and a live
CPU/RAM/GPU/VRAM monitor. Run `python -m pip install -r requirements.txt` after updating.
Telemetry refreshes about once a second while typing and while the agent works.
GPU telemetry uses installed `nvidia-smi`; unsupported or unavailable readings show
`n/a`. RAM means system memory; VRAM means GPU memory. The monitor reports system-wide
usage, not just this process. Redirected output and `TERM=dumb` retain plain text.

Default `/auto` routing selects an installed small model for a brief opening greeting
or short definition/factual question, and the configured task model for context-rich
requests and coding. This is a deterministic heuristic, not an additional AI classifier.
Every route shows the actual selected model and reason. Direct tools bypass inference.
`/fast` forces the small-model preference; `/code` forces the task-model preference;
`/use MODEL` pins a model; `/auto` restores automatic selection. `--model` and `TZ_MODEL`
also pin the model. `TZ_FAST_MODEL` optionally names an already-installed fast model;
otherwise the preference order is gemma3:1b, qwen3:0.6b, qwen3:1.7b. Missing fast models
fall back to the task model. No models are downloaded automatically. Follow-ups retain
the task model to preserve tool and conversation context. Gemma3 1B retains the legacy
CPU workaround. Model headers show runtime-reported family/size/quantization alongside
the actual Ollama alias; aliases are not presented as new foundation models.

`/status` exposes runtime/endpoint and last-response diagnostics; `/hardware` prints
the monitor's latest sample. Repeated ASTRA completion boxes are removed. Inference
still requires a loopback HTTP endpoint and rejects cloud names and remote metadata.
OpenCode labels its model as configured because its stream does not report the served
model. `/status` itself does not perform inference.

Use `/workspace "D:/COMPSCI-RESEARCH/testing"` to select an existing folder during
a session. TZ asks you to trust the folder and clears conversation/backend context.
Overwrite confirmation and backups still apply. For startup, use
`python tz.py --workspace "D:/COMPSCI-RESEARCH/testing"` or set `TZ_WORKSPACE`;
the command-line option takes precedence. Session changes are not persisted.

Verified `.html` and `.htm` writes automatically open a preview on a dynamically
chosen loopback port. Keep TZ running: subsequent edits reload the same tab.
The reload script is injected into the served response, not your saved file.
Relative assets resolve within the selected workspace. OpenCode completed
`write`/`edit` events with a `filePath` also trigger preview opening. If preview
startup fails, TZ attempts to open the file directly and reports the limitation.
Exiting TZ or switching workspace closes the preview server. One-shot `--prompt`
runs open the file directly; use the interactive session for live preview.

## Verification and portability

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests cover original file-request routing, real launch aliases, file verification, command execution, OpenCode routing and model timeout/truncation. CI runs the portable tests on Windows, Linux and macOS. Desktop live tests used Windows, local Ollama and OpenCode 1.18.31; see the build notes for evidence and limits.

- [Laptop setup and sync boundaries](docs/TZ-LAPTOP-SETUP.md)
- [Boris Cherny research, architecture decisions and fixes](docs/TZ-BORIS-AND-BUILD-NOTES.md)

The previous PowerShell application remains at `Start-RAWM.ps1` for legacy desktop-specific features. Older documents and PowerShell tests describe that runtime. Git synchronizes application code, not private conversations, credentials, model weights, or machine-specific launcher paths.
