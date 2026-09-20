# TZ Virtual Desktop UI — Technical Plan — 2026-09-18

Companion to doc 06 (vision). **Built 2026-09-19: phases 0-4 are on `main`** (`app/tz_ui.py`, `ui/`, `config/ui.defaults.json`, `tests/test_ui.py`, `tests/test_commands.py`). The interfaces actually implemented are in `docs/TZ-UI-API-2026-09-19.md`; where this plan and that file differ, the contract file wins. Phase 5 (pywebview) is not started.

## Recommendation in one paragraph

Build the desktop as a **single static HTML/CSS/JS page** served by a **loopback HTTP server inside the running TZ process**, reusing the pattern already in `app/tz_preview.py` (`ThreadingHTTPServer` on `127.0.0.1`, random port, per-session token in the URL). Add a tiny JSON API on that server that calls the existing `Agent` object. Open it with `webbrowser.open()` — exactly how HTML previews open today. Zero new dependencies, works on the laptop the moment it is pulled, and the Windows 3.x look is pure CSS. If Roman later wants a "real app" window with its own icon, wrap the same page in `pywebview` (one optional dependency) — nothing else changes.

## Options considered

| Option | Deps | Win3.x fidelity | Effort | Verdict |
|---|---|---|---|---|
| **A. HTML page + loopback server (in-process)** | none | excellent (CSS) | low | **Do this.** Same trick as `tz_preview.py`. |
| B. Same page inside `pywebview` | `pywebview` (uses Edge WebView2 on Win10, already present) | excellent | +1 day | Phase 5 upgrade, optional. |
| C. `tkinter` native window | none (stdlib) | poor — bevels/fonts fight you | medium | No. Looks wrong, and dragging overlapping child windows in Tk is painful. |
| D. Textual/Rich TUI "desktop" in the terminal | `textual` | fun but it is still a terminal | medium | No. Roman wants a window, not a fancier terminal. |
| E. Electron / Tauri | Node toolchain, hundreds of MB | excellent | high | No. Violates the no-heavy-deps constraint. |

## Architecture

```
 PowerShell / cmd                       default browser (or pywebview)
 ┌─────────────────────┐   HTTP (loopback, token)   ┌────────────────────────┐
 │ tz.py  → Terminal   │◄──────────────────────────►│ ui/index.html          │
 │   Agent (one object)│   GET  /<token>/ui/...     │  desktop.css  (Win3.x) │
 │   ├─ turn()         │   POST /<token>/api/turn   │  desktop.js  (windows) │
 │   ├─ messages[]     │   GET  /<token>/api/events │  icons/*.svg           │
 │   ├─ save()/state   │   GET  /<token>/api/sessions│                       │
 │   └─ preview (HTTP) │   ...                      └────────────────────────┘
 └─────────────────────┘
        ▲ emit() fan-out: every line printed in the terminal is also queued for the UI
```

Key decisions:

1. **One Agent, two faces.** The terminal and the desktop share `agent.messages`, the session id, routing, and the model. A turn started in the UI shows up in the terminal log and vice versa. Implement by wrapping `agent.emit`: the terminal's `emit` stays, plus a `Broadcast` that pushes the same lines into a per-client `queue.Queue` for Server-Sent Events.
2. **Serialize turns.** `Agent.turn()` is not thread-safe (it mutates `messages`). Put a `threading.Lock` around turn execution; the UI's `POST /api/turn` returns `409 busy` if the terminal is mid-turn, and the terminal shows `[ui] running: <text>` when the UI owns the turn. Simplest correct behavior; refine later.
3. **Confirmations.** `agent.confirm` is a callable. When a turn originates from the UI, set a temporary confirm that publishes `{"type":"confirm","id":..,"question":..}` on the event stream and blocks (with timeout) on an answer posted to `POST /api/confirm`. The UI renders a Win3.x message box. When the turn originates from the terminal, the terminal's `ask()` still handles it.
4. **Static assets vendored.** `ui/` directory in the repo: `index.html`, `desktop.css`, `desktop.js`, `icons/*.svg`. No CDN, no npm. Roman's laptop gets it via `git pull`.
5. **Security = same as preview today.** Bind `127.0.0.1`, random port, 32-hex token in every path, `Cache-Control: no-store`, reject any path without the token. Add `Content-Security-Policy: default-src 'self'` so the page can never load anything external. The API only exposes what the terminal already lets Roman do.

## Server: extend `tz_preview.py` or add `tz_ui.py`?

Add **`app/tz_ui.py`** with a `Desktop` class that owns its own `ThreadingHTTPServer` (do not overload `Preview`, which is deliberately file-only). Share the helper bits by import. ~200 lines.

Endpoints (all under `/<token>/`):

| Method | Path | Does |
|---|---|---|
| GET | `ui/` and `ui/<asset>` | Serve files from `<repo>/ui/`. Path-traversal guarded like `Preview`. |
| GET | `api/state` | `{label, model, task_model, routing, session_id, workspace, specs: {...from Hardware.collect()}}` |
| GET | `api/events` | SSE stream. Event types: `line` (emit text), `stream` (partial model tokens if the terminal already has them separated; otherwise reuse `line`), `tool`, `turn_start`, `turn_end`, `confirm`, `status` (the CPU/RAM/GPU readings `Hardware.run()` already produces every second). |
| POST | `api/turn` | `{"text": "..."}` → runs `agent.turn(text)` on a worker thread, returns `{"accepted": true}` or `409`. Slash commands from the main loop (`/clear`, `/use`, `/models`, `/auto`, `/status`) need to move into a shared `command(text)` function so both faces can call them — that refactor of `main()` is Phase 1's real work. |
| POST | `api/confirm` | `{"id": .., "answer": true/false}` |
| GET | `api/sessions` | Reads `data/tz/*.json`, returns `[{id, started, title: first user message[:60], turns}]` newest-first. |
| POST | `api/sessions/<id>/resume` | Same logic as `--resume` in `main()`; extract that into `Agent.resume(id)`. Refuses while a turn is running. |
| GET / PUT | `api/config` | Read/write the `ui` section. **Two layers:** tracked defaults in `config/ui.defaults.json` (built-in presets, default wallpaper, icon layout — this is what the laptop gets via `git pull`) merged under Roman's per-machine overrides in `config/tz.local.json` (gitignored): `{"ui": {"open": "ask", "wallpaper": "#008080", "presets": [...]}}`. PUT writes only to `tz.local.json`, whitelisted keys only. |
| POST | `api/open` | `{"url": "..."}` → `agent.tool('open_target', {...}, explicit=True)`. Used by the Browser icon and "Open in browser" presets. |

## Terminal changes

In `app/tz_agent.py` `main()` after `terminal.specs()`:

```
mode = settings().get('ui', {}).get('open', 'ask')     # ask | always | never
if mode == 'always' or (mode == 'ask' and terminal.yes_no('Would you like to open UI? (Y/N)', default=False)):
    from app.tz_ui import Desktop
    agent.desktop = Desktop(agent, terminal); agent.desktop.open()
```

Plus commands: `/ui` (open, starting the server if needed), `/ui close`, `/ui always|never|ask`. Add a `yes_no()` helper to `Terminal` using prompt_toolkit's `PromptSession` with a one-key validator; when stdin is not a TTY (tests, `--prompt`), it returns the default without prompting.

`--prompt` one-shot mode never opens the UI.

## Front end

`ui/desktop.js`, plain ES2020, no framework:

- `WindowManager`: creates `.win` elements with title bar, system-menu box, min/max boxes; drag via pointer events on the title bar; z-order on mousedown; minimize → icon at the desktop bottom; positions persisted in `localStorage` (per-viewer convenience only, fine to lose).
- `Icons`: reads the icon list from `/api/config` (`presets`) merged with the built-in set (Start, Chat, Search, Browser, Files, Settings, Clock). Double-click opens the window; single click selects (dotted rect). Keyboard: arrows + Enter, for the authentic feel.
- `Chat` window: renders the event stream; `Me >` input box; `◀ n/N ▶` session pager backed by `/api/sessions`.
- `Search` window: grid of preset sub-icons; "+ New preset" dialog with *Phrase*, *Mode* (Ask TZ / Open in browser), *Icon* (pick from vendored set). Saves via `PUT /api/config`.
- `Settings` window: wallpaper color picker (native `<input type=color>` restyled), image wallpaper by workspace path (served through the existing `Preview` server or a new `api/file` endpoint restricted to image types), label, model dropdown from `/api/state`, routing radio, "open UI on start" radio, startup chime checkbox.
- `Boot` overlay: black, monospace, prints `/api/state` specs lines with a 40 ms per-line delay, then removes itself. Click to skip.

`ui/desktop.css`: tokens for the palette (`--desk`, `--chrome`, `--title-active`, `--title-inactive`, `--bevel-light`, `--bevel-dark`), 3-D bevel mixin via `box-shadow` insets, `image-rendering: pixelated` for icons, `MS Sans Serif` font stack. Prior art to *look at, not vendor without checking the license*: the "98.css" and "7.css" projects show how the bevels are done with two inset box-shadows.

## Phases (each = one commit, one push, one laptop pull)

| Phase | Deliverable | Touches | Done when |
|---|---|---|---|
| **0** | `Would you like to open UI? (Y/N)` prompt + `/ui` command + `ui.open` config key. Opens a placeholder `ui/index.html` that says "TZ desktop — coming soon" with the boot screen. | `tz_agent.py main()`, `tz_terminal.py yes_no()`, new `tz_ui.py` (static serving only), `ui/index.html` | Roman types `roman`, hits Y, a teal page opens; `N` behaves as today; tests green; `--prompt` unaffected. |
| **1** | Shared command layer + `api/state`, `api/turn`, `api/events`. Chat window works for the current session. | `Agent.command()` refactor out of `main()`, `tz_ui.py` API, `desktop.js` Chat | Typing in the Chat window runs a turn that also prints in the terminal; typing in the terminal shows in Chat. |
| **2** | Window manager + icons + Start/Chat/Clock/Browser windows. Chat session pager. | `desktop.js`, `desktop.css`, `icons/`, `api/sessions`, `Agent.resume()` | Roman can close Start, open Chat, page back to yesterday's session, and continue it. |
| **3** | Search presets (built-ins + "+ New preset"), Files window. Depends on doc 05 B1/B4 (`local_time`, browser intents) so presets are instant. | `api/config`, `api/open`, `desktop.js` Search/Files | "Time in Japan" preset answers in < 1 s; "Look up X" preset opens the real browser. |
| **4** | Settings window: wallpaper, label, model, routing, open-on-start, chime. Confirm dialogs for `run_command`. | `api/config` writes, `api/confirm`, `desktop.js` Settings | Roman "sets the background and stuff". |
| **5 (optional)** | `pywebview` wrapper so the desktop is its own window with a taskbar icon; Windows shortcut via `install.py --desktop`. | `tz_ui.py`, `tz_install.py`, `requirements.txt` (optional extra) | Same page, native window. |

## Testing

- Unit: `tests/test_ui.py` — start `Desktop` on a random port with a fake agent, assert token-less requests 404, `api/state` shape, `api/sessions` sorting, `api/config` whitelist rejects unknown keys, `api/turn` returns 409 while the lock is held.
- Manual: add a "UI" section to `TZ-QUICK-TEST-GUIDE.md` per phase.
- Browser: use Claude Code's built-in browser (`preview_start` with the token URL printed by `/ui`) to screenshot each phase before committing.

## Risks

- `webbrowser.open()` on Windows sometimes opens in an existing window's new tab — fine, but the boot screen "ceremony" is weaker in a tab. Phase 5 fixes that.
- Streaming: `Terminal.emit()` currently handles partial lines for the Rich renderer; make sure the broadcast hook receives complete lines or explicit `stream` chunks, or the UI will show token soup. Read `emit()`/`flush_stream()` (`tz_terminal.py` lines 264–302) before wiring.
- Threading: prompt_toolkit's input loop and a worker thread running `agent.turn()` both call `terminal.emit`. Rich's `Console` is not thread-safe by default; wrap `emit` in a lock or use `console.print` from the main thread via a queue.
