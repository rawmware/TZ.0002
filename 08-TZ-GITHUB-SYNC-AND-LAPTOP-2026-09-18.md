# TZ GitHub Sync and Laptop — 2026-09-18

Roman's requirement, verbatim: *"github should be updated too, so my desktop and laptop have the same application — I haven't tested on my laptop yet but it's important to note."*

Rule for every conversation from now on: **a phase is not done until it is pushed to `main`.** Desktop is the only machine that has run the current build; the laptop has never been tested.

## Repo facts (verified 2026-09-18)

- Remote: `https://github.com/rawmware/TZ.0002.git`, branch `main`, HTTPS via Git Credential Manager. No `gh` CLI on this machine — use plain `git`.
- Local identity: `rawmware` / `rjcottonham@gmail.com`.
- `.gitattributes` is `* -text` and `core.autocrlf=false`, so files go up byte-for-byte. Do not "fix" line endings.
- Local branch is even with `origin/main` at `a38469c`. Only untracked files differ (below).
- **Gitignored, therefore per-machine and NOT synced:** `data/` (sessions, events, audit), `config/tz.local.json` (passcode, launcher, and the planned `ui` section), `config/settings.local.json`, `workspace/`, `models/*.gguf`, `archive/`, `*.backup-*`. Consequence for the UI plan: default presets and default wallpaper must live in a **tracked** file (e.g. `config/ui.defaults.json`) with `tz.local.json` holding only Roman's overrides — otherwise the laptop desktop would be empty.

## What to commit right now (before any code)

```bash
git add 04-TZ-HANDOFF-INDEX-2026-09-18.md 05-TZ-BUGS-AND-RELIABILITY-2026-09-18.md 06-TZ-VIRTUAL-DESKTOP-UI-VISION-2026-09-18.md 07-TZ-VIRTUAL-DESKTOP-UI-TECH-PLAN-2026-09-18.md 08-TZ-GITHUB-SYNC-AND-LAPTOP-2026-09-18.md TZ-PRODUCT-ASSESSMENT-2026-09-17.md TZ-QUICK-TEST-GUIDE.md
```

```bash
git commit -m "Add 2026-09-18 planning docs: bugs, virtual desktop UI, sync"
```

```bash
git push origin main
```

Leave untracked (scratch, per memory): `agent-smoke.html`, `hello.md`, `note.md`. If they keep showing up, add them to `.gitignore` in the same commit.

## Commit cadence for the work in docs 05 and 07

One commit per bug or phase, so the laptop can pull a known-good point and Roman can bisect if something regresses:

| Commit | Contents | Verify before push |
|---|---|---|
| `Fix browser intents and system prompt (B1)` | `direct()` regexes, `SYSTEM` sentence, tests | `python -m unittest discover -s tests -p "test_*.py"` green; manual test 1 in doc 05 |
| `Replace search provider and add relevance guard (B2, B3)` | `web_search`, tests | manual test 3 |
| `Add local_time tool and time intents (B4)` | new tool, alias table, tests, maybe `tzdata` in `requirements.txt` | manual test 2 |
| `Fix /auto reset, fuzzy /use, VRAM warning (B5)` | `main()`, tests | manual tests 4–5 |
| `Warm models on start; fix stray Canceled line (B6)` | `main()`, `tz_terminal.py` | manual test 6 |
| `UI phase 0: Y/N prompt and placeholder desktop` | doc 07 phase 0 | Y opens page, N unchanged |
| `UI phase 1 …` and so on | | |

Commit message trailer per the session rules: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

After each push, append a line to the table at the bottom of this file with the commit hash, so the laptop knows what to pull.

## Laptop: first-time test plan

`docs/TZ-LAPTOP-SETUP.md` already has the install steps. Do them, then run this checklist and record results here (or in a new `TZ-LAPTOP-TEST-RESULTS-<date>.md`):

1. `git clone https://github.com/rawmware/TZ.0002.git` (or `git pull` if it exists) and note the hash: `git log -1 --oneline`.
2. `python --version` (need 3.10+), `ollama --version`, `ollama list` — which of `tz-agent:latest`, `gemma3:1b` exist? Run `python install.py --setup-model --desktop` if `tz-agent` is missing.
3. `python -m pip install -r requirements.txt`
4. `python tz.py --doctor` → must print `Ready: tz-agent:latest`.
5. `python -m unittest discover -s tests -p "test_*.py"` → note the count; desktop is 54 green.
6. `python tz.py` → specs box shows the laptop's CPU/GPU/VRAM correctly (`Hardware.collect()` uses `nvidia-smi` and WMI; a laptop with Intel/AMD graphics or no dGPU is the first time that code path runs without an NVIDIA card — watch for a crash or a blank GPU line).
7. Register the launch word: inside TZ, `/passcode roman` — `tz.local.json` is per-machine, so the laptop does not know `roman` until this is done.
8. Run the six manual tests from doc 05 (after those fixes are pushed).
9. If the UI phase 0 is pushed: `Y` at the prompt opens the page in the laptop's default browser.

Expected differences on the laptop, not bugs: smaller VRAM (maybe none) so `tz-agent:latest` runs slower or on CPU; `gemma4:26b`/`qwen3.6` should simply not be installed there. The B5 VRAM warning should trigger correctly on the laptop — that is a good test of it.

Things that could genuinely break on the laptop and have never been exercised:
- `tz_terminal.py` `Hardware.graphics()` without NVIDIA.
- `install.py --desktop` shortcut creation on a different user profile path.
- OneDrive: the desktop repo lives under `OneDrive\Documents`. If the laptop clones into OneDrive too, the same folder will sync **both** ways and fight git. Clone the laptop copy **outside** OneDrive (e.g. `C:\Users\<user>\TZ`) — the whole point of GitHub is to be the sync channel.

## Push log

| Date | Hash | What | Laptop pulled? |
|---|---|---|---|
| 2026-09-17 | `a38469c` | `/team` subagents + status line | no |
| 2026-09-18 | _(fill in)_ | planning docs 04–08 | no |
