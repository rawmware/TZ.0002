# TZ Handoff Index — 2026-09-18

**Start here.** Roman (the user) wrote this set of plans with Claude on 2026-09-18 so a fresh conversation can pick up the work cold. Read the docs in this order:

| # | File | What it is |
|---|------|------------|
| 04 | `04-TZ-HANDOFF-INDEX-2026-09-18.md` | This file. Ground truth, constraints, definition of done. |
| 05 | `05-TZ-BUGS-AND-RELIABILITY-2026-09-18.md` | Bugs observed in the 2026-09-18 test session, root causes traced to code, fixes. **Do this first.** |
| 06 | `06-TZ-VIRTUAL-DESKTOP-UI-VISION-2026-09-18.md` | The "computer inside a window" UI concept (Windows 3.x aesthetic). Concept only; Roman is not ready to build it yet. |
| 07 | `07-TZ-VIRTUAL-DESKTOP-UI-TECH-PLAN-2026-09-18.md` | How the UI would actually be built on top of the existing code, in phases. |
| 08 | `08-TZ-GITHUB-SYNC-AND-LAPTOP-2026-09-18.md` | Keeping GitHub current so desktop and laptop run the same build. Laptop is **untested** so far. |

Roman's own raw notes and the terminal transcript that triggered all of this live outside the repo at `D:\COMPSCI-RESEARCH\Html's\ollama ouput\readME3.MD`. Doc 05 quotes the relevant parts, so you do not need that file.

## What Roman said, in one paragraph

He is enjoying the app. Two problems: (1) sometimes it does not do what he says and he cannot tell why — the same request ("open the browser and look up X") works one run and is refused the next; (2) web search returns garbage. Separately, he is conceptualizing his own UI: not a real VM, but the *aesthetic* of a computer inside a window — Windows 3.x Program Manager look — where desktop icons are tasks or phrases he says a lot ("Search", "Start", "Chat"), and where the terminal stays the entry point: after launching `roman`, TZ asks `Would you like to open UI? (Y/N)`. He wants the plan written down now, built later, and GitHub kept in sync because he has not tested on the laptop yet.

## Ground truth about the repo (verified 2026-09-18)

- Repo: `C:\Users\rjcot\OneDrive\Documents\ChatGPT\TIZI`, remote `https://github.com/rawmware/TZ.0002`, branch `main`. Last commit `a38469c Add /team: bounded local subagents...`.
- Entry point: `TZ.cmd` → `tz.py` → `app/tz_agent.py` `main()`. `rom.ps1` is a wrapper that calls `TZ.cmd`; `roman` in PowerShell and in cmd both end up running the same Python. The shell is **not** the source of the inconsistency (see doc 05).
- Core files: `app/tz_agent.py` (700 lines: `Agent`, `TOOLS`, `route()`, `direct()`, `turn()`, `converse()`, `execute()`), `app/tz_terminal.py` (Rich + prompt_toolkit UI), `app/tz_team.py` (`/team`), `app/tz_preview.py` (loopback HTTP preview server with a per-session token — relevant to the UI plan), `app/tz_opencode.py`, `app/tz_install.py`.
- Tools the model can call: `file_read`, `file_write`, `list_files`, `fetch_url`, `web_search`, `run_command`, `open_target`, `system_info`.
- Sessions persist as JSON in `data/tz/<id>.json` (`messages`, `model`, `task_model`, `routing`). This is what a "Chat" window in the UI would cycle through.
- Config: `config/settings.json` (legacy RAWM settings; `interface.passcode: "roman"`), `config/tz.local.json` (`passcode`, `launcher`). Note the two files disagree on the label.
- Tests: `python -m unittest discover -s tests -p "test_*.py"` — 54 green as of 2026-09-17. Keep it green.
- Ollama models installed: `tz-agent:latest` (Qwen3 4B, the task model), `qwen3:4b`, `qwen3:4b-instruct-2507-q4_K_M`, `gemma3:1b` (fast model), `gemma4:26b`, `qwen3.6:latest` (36B MoE). GPU is an RTX 2080 SUPER with **8 GB VRAM** — the two big models do not fit and time out.
- Untracked scratch in root right now: `TZ-PRODUCT-ASSESSMENT-2026-09-17.md`, `TZ-QUICK-TEST-GUIDE.md`, `agent-smoke.html`, `hello.md`, `note.md`. See doc 08 for what to commit.

## Hard constraints

1. **No new external dependencies without a reason.** Current deps: `rich`, `prompt_toolkit`, `psutil`, `pypdf`. Everything else is stdlib. The UI plan honors this.
2. **Terminal stays the entry point.** Roman explicitly wants to keep launching from PowerShell/cmd with `roman`. The UI is opt-in via the Y/N prompt.
3. **Local only.** Ollama on `127.0.0.1:11434`. Any UI server must be loopback-only with a token, like `tz_preview.py` already does.
4. **Same build on desktop and laptop.** Every completed phase gets committed and pushed. Doc 08.
5. **Windows-first.** Windows 10, Python 3.10.6. Keep Unix paths working but do not test on them.

## Definition of done for the next conversation

- [ ] Doc 05 bugs B1–B6 fixed, each with a unit test, `unittest` still green.
- [ ] `Would you like to open UI? (Y/N)` prompt exists (doc 07, Phase 0) even if the UI behind it is a placeholder page.
- [ ] Commit per phase, push to `main`, and note in doc 08 which commit hash the laptop should pull.
- [ ] Doc 06/07 updated with any decisions made while building.

## Working notes for the next Claude

- Roman writes fast and informally; read intent, not spelling. When he says "passcode" he means the launch word (`roman`), not a password — `install.py`/`/passcode` registers it as a command.
- When running `tz.py --prompt "/team ..."` from Git Bash set `MSYS_NO_PATHCONV=1` or `/team` becomes a Windows path.
- Heredoc-fed Python patches mangle `\b` and `·` on this machine; write patch scripts with the Write tool.
- Leave scratch outputs (`hello.md`, `note.md`, `agent-smoke.html`) untracked.
