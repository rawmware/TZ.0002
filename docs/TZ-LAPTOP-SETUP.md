# Desktop and laptop: same TZ build

The canonical application is now `tz.py`, a Python 3.10+ terminal agent. PowerShell is optional. The old `Start-RAWM.ps1` implementation remains available for legacy features.

On the laptop, install Python 3.10+, Node.js/npm, Git, and Ollama, then start Ollama. Clone this repository (or pull it if already cloned):

```text
git clone https://github.com/rawmware/TZ.0002.git
cd TZ.0002
python -m pip install -r requirements.txt
npm i -g opencode-ai
python install.py --setup-model --desktop
python tz.py --doctor
```

Use `python3` instead of `python` on macOS/Linux. `--desktop` creates a Windows shortcut only; on Unix, add `~/.local/bin` to PATH or run `python3 tz.py` directly. `sh tz` is also supported. No user-specific desktop paths are committed.

The model setup downloads Qwen3 4B Instruct (~2.5 GB) and creates the `tz-agent:latest` alias with 16K context. It reuses model weights rather than duplicating them. OpenCode uses the same local Ollama model. Its npm package may fetch its runtime/provider dependencies on first use. A cloud account/API key is not required for this configuration. Smaller laptops may run more slowly; `--model` or `/use` selects another installed model.

Open the single **TZ** shortcut, or type `tz`, `roman`, or `rom`. Inside TZ, `/passcode nova` registers the command `nova` and changes the prompt. Existing aliases remain available for compatibility. This is a launch name, not a password. On a second machine, set the name there too: local PATH entries and machine paths must be registered locally.

Try:

```text
/read "path/to/AGENTS.md"
/read "path/to/paper.pdf" 0 6000
/fetch https://example.com
/search projects using codex
/opencode Create hello.html with a heading Hello Roman and read it back.
/opencode
```

The last command opens OpenCode's interactive UI for longer tasks and interactive command approvals. Natural coding requests also route to OpenCode when installed. Follow-up coding requests reuse its session. Direct file reads, URL fetches and searches work even with Ollama stopped.

New files written by TZ's built-in tool are read back and hashed. Replacing an existing file through that tool asks once and saves a backup. OpenCode's build agent can edit workspace files directly; inspect its diffs in Git. OpenCode shell commands/outside-workspace access require its interactive approval; headless tasks report denied requests instead of pretending success. `/run ["python", "script.py"]` is an explicit user command and runs directly, without assuming a shell.

Code syncs through Git. Local conversations (`data/`), OpenCode sessions, models, credentials, local settings and launch registrations do **not** sync through this public repository. Use the same code and reinstall local dependencies on each machine. To resume a local TZ session, use `python tz.py --resume SESSION_ID` from `/status`.

Verification: `python -m unittest discover -s tests -p test_tz.py -v`. This checks tools, routing, launch aliases, argument validation, file verification and incomplete/timeout handling without downloading a model. Legacy PowerShell tests target the previous runtime and are not the new Python test suite.
