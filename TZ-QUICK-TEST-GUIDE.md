# TZ — Quick Test Guide

Everything below was checked against `app/tz_agent.py` on 2026-09-18. Commands are typed at the TZ prompt unless marked as a shell command.

## 1. Start it

Make sure Ollama is running (system tray icon, or run `ollama serve` in a terminal). Then from the `TIZI` folder:

```bash
python tz.py
```

Useful variants:

```bash
python tz.py --doctor                       # checks Python, Ollama, models, tools — run this first
python tz.py --workspace "D:/some/project"  # start inside a different folder (TZ only writes there)
python tz.py --model qwen3:4b               # pin a model for the whole session
python tz.py --prompt "read README.md"      # run one request and quit (good for scripting)
```

Type `/help` any time for the full list. `/exit` quits. `Ctrl+C` cancels a model mid-answer.

## 2. Pick a model

```text
/models                  list what Ollama has installed
/use qwen3:4b            switch to that model (must be in /models)
/use tz-agent:latest     back to the default (Qwen3 4B, 16K context)
/status                  show which model is active and why
```

Installed on this machine right now: `tz-agent:latest` (default), `qwen3:4b`, `qwen3:4b-instruct-2507-q4_K_M`, `gemma3:1b` (fast/tiny), `gemma4:26b` (18 GB, slow but strong), `qwen3.6:latest` (23 GB).

Routing modes (how TZ chooses a model when you *haven't* pinned one):

```text
/auto    default — tiny model for "hi"/"what is X", task model for everything else
/fast    always prefer the small model (gemma3:1b) — quick chat, weak at tools
/code    always use the task model
```

Every answer prints a `[route]` line showing which model was actually used. `/verbose` hides/shows those lines.

## 3. Look things up on the web

```text
/fetch https://example.com                     pull the text of one page
/search local llm agents                       web search, returns links + snippets
/search codex github                           "github"/"codex" in the query → GitHub repo search
```

Plain English works too:

```text
summarize https://en.wikipedia.org/wiki/Ollama
search the web for qwen3 benchmarks
```

`/fetch` and `/search` run instantly with no model. If you *ask* a question ("what does the Ollama README say about GPU support?") the model decides to call `fetch_url`/`web_search` itself — slower, and worth testing because that's where small models fail.

## 4. Open a browser / an app

```text
/open https://github.com/rawmware/TZ.0002      opens in your default browser
/open "D:/downloads/report.pdf"                opens with the default app for that file type
/open index.html                               HTML inside the workspace → live-reload preview server
```

Also: `open https://...` in plain English does the same thing.

## 5. Read files

```text
/read README.md                          first 12,000 characters
/read "D:/downloads/paper.pdf" 0 6000    PDF, from character 0, 6,000 characters
/read notes.txt 12000                    continue from character 12,000
list the workspace files
show system info
```

Or just: `read README.md`, `summarize "D:/docs/plan.md"`.

## 6. Write files (the main thing to test)

```text
create a file "hello.html" containing "<h1>Hello</h1>"      instant, no model
Create an HTML page with a dark theme and a heading Hello Roman, then verify it.
```

The second one uses the model. What to watch for:
- It should call `file_write`, then `file_read` to verify, then stop.
- New files write immediately. **Replacing an existing file asks you `[y/N]` and saves a backup** under `data/tz/backups/`.
- Writes outside the workspace are refused.
- `.html` files auto-open in a live preview tab; edit again and the tab reloads.

## 7. Run a command

```text
/run ["python", "--version"]
/run ["git", "status"]
```

Arguments are a JSON array, no shell — so no pipes or `&&`. Explicit `/run` executes immediately; a command the *model* wants to run asks you first. 60-second limit.

## 8. Subagents

```text
/team Compare the README and the future-architecture doc and list contradictions
/team --write --slots 2 Write hello.py | Write a test for hello.py
```

Lead plans 2–4 workers (or you split with `|`). Workers are read-only unless `--write`. Every run leaves a receipt in `data/tz/teams/`.

## 9. Coding via OpenCode (optional — needs `npm i -g opencode-ai`)

```text
/opencode Build a simple landing page in this workspace
/opencode                     opens the full OpenCode TUI
```

Sentences starting with build/create/fix/… that mention code/app/html/etc. route to OpenCode automatically if it's installed.

## 10. Suggested 10-minute smoke test

1. `python tz.py --doctor`
2. `python tz.py` → `/models` → `/use qwen3:4b` → `hi` (should route to gemma3:1b under `/auto`)
3. `/fetch https://example.com`
4. `search the web for ollama modelfile syntax`
5. `create a file "t.html" containing "<h1>test</h1>"` → preview tab should open
6. `Add a paragraph under the heading in t.html and verify it.` → expect the overwrite prompt + backup
7. `/run ["python", "--version"]`
8. `/team Summarize README.md | List every /command in app/tz_agent.py`
9. `/status`, `/hardware`, `/exit`

If a step misbehaves, `data/tz/events.jsonl` has the tool-by-tool audit log and `data/tz/<session-id>.json` has the full conversation — `python tz.py --resume <session-id>` picks it back up.

## 11. After the 2026-09-19 fixes (docs 05/07) — six manual checks

Run `roman` and type, in order:

1. `open the browser and look up the time in japan` → your real browser opens a Google search; the log shows `[route] DIRECT · open_target · no model needed`.
2. `what time is it in japan` → instant `local_time` answer with `Asia/Tokyo`; no model.
3. `look up who james gandolfini was` → either relevant search results (DuckDuckGo first, Bing RSS second) or a clear `Search returned no relevant results ... Use /open` error. **Never** an invented biography. If the model still answers from memory, that is B3; note the wording.
4. `/use qwen 3.6` → resolves to `qwen3.6:latest` and asks `... 22 GB; this GPU has 8 GB VRAM ... Continue? [y/N]` — answer `n`.
5. `/auto` → prints `Routing: AUTO · task model tz-agent:latest`.
6. `hello?` → answer in under 3 s once the warm-up has run (it starts right after the specs box).

Also: Ctrl+C at the idle `Me >` prompt must NOT print "Canceled. Partial output is unverified." any more; only a Ctrl+C during a running turn does.

## 12. The desktop UI (Windows 3.x window in the browser)

- After the specs box TZ asks `Would you like to open UI? (Y/N)  [Enter = N]`. `Y` opens the desktop in your default browser; the terminal keeps working. `/ui` opens it later, `/ui close` stops it, `/ui always|never|ask` remembers the answer in `config/tz.local.json`.
- Boot screen prints the specs, then the Program Manager desktop appears with Start, Chat, Search, Browser, Files, Settings and Clock.
- **Start**: type `what time is it in portsmouth nh` → the Chat window opens with the answer. Type `hello?` → streamed model answer; the same lines print in the terminal.
- **Chat**: `◀ ▶` pages through saved sessions (`data/tz/*.json`) and resumes them; `New` starts a fresh one. Typing in the terminal shows up here too.
- **Search**: double-click `Time in Japan` (instant, no model) and `Latest news` (opens Google in the real browser). `+ New preset` saves to `tz.local.json` → `ui.presets`; right-click/Delete removes.
- **Files**: File Manager over the workspace, read-only; click a text file to view it.
- **Settings**: wallpaper colour/image, model + AUTO/MANUAL, "Open UI on start", startup chime. OK writes `tz.local.json` → `ui`.
- An overwrite (`create "x.txt" containing "a"` twice) pops a Yes/No message box in the desktop when the request came from the desktop; from the terminal it still asks in the terminal.
- Only `127.0.0.1`, random port, 32-hex token in the URL, CSP `default-src 'self'`; nothing external is loaded.
