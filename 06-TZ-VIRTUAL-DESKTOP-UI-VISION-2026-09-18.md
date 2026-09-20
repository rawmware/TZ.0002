# TZ Virtual Desktop UI — Vision — 2026-09-18

**Status: concept.** Roman is conceptualizing, not committing to build. This doc captures the idea in his words and turns it into concrete screens so the next conversation can build it when he says go. The technical plan is doc 07.

## The idea, in Roman's words (lightly cleaned up)

> The internal GUI is nice but having my own little app would be cool. It doesn't need to be a real virtual desktop or VM — what if we captured the *aesthetic* of it? A computer within a window. Philosophically it's cool to have this powerful AI and have it look like a computer on my computer — that Jarvis "wake up" feeling.
>
> I'm heavily imagining the Windows 3 aesthetic. The desktop icons would be different tasks, or key phrases I say a lot. A "Search" icon would hold my predetermined questions — like "look up the time in Japan right now" — and it would open the browser and type it in for me. Modern browsers have AI built in, so just typing it in the address bar gives way more than the AI funnelling messages to me.
>
> One icon would be "Start" — the initial sequence. One would be "Chat" — the continuation of the conversation. If you closed the Start window you could use Chat to cycle through conversations and pick up where I left off.
>
> Initially I still open it from the terminal/PowerShell — we worked hard on that. After typing `roman`, it would say **Would you like to open UI? (Y/N)**. Hit Y and the virtual desktop opens. I could set the background and stuff in there. That's where this gets cool.

## Design principles

1. **A computer inside a window.** The UI is one window that *is* a retro desktop: wallpaper, desktop icons, a Program Manager-style shell, movable overlapping child windows with the classic title bars. It never pretends to be a real OS; it is a face for TZ.
2. **The terminal is still the brain.** The desktop is a remote control for the same `Agent` running in the terminal. Anything you do in the desktop is visible in the terminal log, and the terminal keeps working while the desktop is open.
3. **Icons are verbs Roman actually uses.** Not a file system. Each icon is a task or a phrase. Roman can add his own.
4. **Prefer the real browser for "look up X".** A preset that opens Google in his real browser beats the model summarizing search snippets (doc 05, B1/B2).
5. **Wake-up moment.** Launch has a little ceremony: the terminal asks Y/N, the window opens on a boot screen for a second ("TZ · LOCAL AGENT · loading…", hardware line from `/specs`), then the desktop appears. Cheap to do, and it is the whole point.

## Visual language: Windows 3.x

Reference: the three screenshots Roman attached (Windows 3.1 Program Manager with Main/Accessories groups, Clock, File Manager, Reversi; Windows 3.1 Solitaire with Help window; a Windows 95/98 teal desktop as a secondary reference).

- **Palette:** desktop background `#008080` teal (Win95) or a Roman-chosen wallpaper; window chrome `#C0C0C0` gray; active title bar `#000080` navy with white text; inactive title bar gray; 1-px black outline, 2-px 3-D bevels (white top-left, dark gray bottom-right).
- **Typography:** system-style bitmap look — "MS Sans Serif" fallback chain: `"MS Sans Serif", "Microsoft Sans Serif", Tahoma, sans-serif`, 11–12 px, no anti-aliasing tricks needed.
- **Windows:** title bar with system-menu box on the left, minimize/maximize boxes on the right (Win 3.x style ▼ ▲), draggable by title bar, resizable from the bottom-right, minimize collapses to an icon at the bottom of the desktop (Win 3.x behavior — no taskbar). Optional Win95 taskbar mode later.
- **Icons:** 32×32, 16-color look. Draw them as inline SVG or tiny PNGs vendored in the repo — **no CDN** (must work offline and on the laptop). Icon labels white-on-teal with the classic dotted focus rectangle when selected.
- **Sounds:** none by default. A settings toggle for a startup chime is a nice-to-have.

## Screens

### 1. Terminal prompt (Phase 0)

```
┌─ This machine ─────────────────────────────────────────┐
│  ...specs box as today...                              │
└────────────────────────────────────────────────────────┘
Would you like to open UI? (Y/N)  [Enter = N]  (set "ui": "always"|"never"|"ask" in config/tz.local.json)
```

- `Y` opens the desktop in the default browser (or a pywebview window, doc 07) and returns to the normal `Me >` prompt. The terminal keeps running.
- `N`/Enter → today's behavior.
- `/ui` command opens it later; `/ui close` shuts the server.

### 2. Boot screen (1–2 s)

Black screen, white monospace: the same header lines the terminal prints (`TZ | LOCAL AGENT | AUTO`, model, CPU/GPU/VRAM lines), then fades to the desktop. Skippable by click.

### 3. Desktop

ASCII mockup of the default layout:

```
╔══════════════════════════════════════════════════════════════════════╗
║ ▬  TZ — Program Manager                                     ▼  ▲    ║
║ File  Options  Window  Help                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  [▶]        [💬]        [🔍]        [🌐]        [📁]        [⚙]      ║
║  Start      Chat        Search      Browser     Files       Settings ║
║                                                                      ║
║                 ┌─ Chat ───────────────────────────────▼─▲─┐         ║
║                 │ Session 20260918-003539-6eba7b  ◀ 3/3 ▶  │         ║
║                 │ ─────────────────────────────────────── │         ║
║                 │ Me > look up who james gandolfini was   │         ║
║                 │ AI > James Gandolfini was ...           │         ║
║                 │ Me > opent the web rbwoser so i can ... │         ║
║                 │ [tool] open_target ...                   │         ║
║                 │ ─────────────────────────────────────── │         ║
║                 │ Me > _                            [Send] │         ║
║                 └──────────────────────────────────────────┘         ║
║                                                                      ║
║  ┌─ Clock ──┐                                                        ║
║  │  🕓 3:34 │                                                        ║
║  └──────────┘                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
 tz-agent:latest · AUTO · TIZI  |  CPU 6%  |  RAM 12.4/31.8 GB  |  GPU0 3.6/8 GB
```

The bottom line mirrors the terminal's persistent status line (already implemented in `tz_terminal.py`).

### 4. Icons (default set)

| Icon | Opens | Behavior |
|---|---|---|
| **Start** | The "initial sequence" window | New session. Shows the greeting, the specs box, and a text field. Equivalent to a fresh `roman` launch. Closing it does not end the session. |
| **Chat** | Conversation browser | Lists sessions from `data/tz/*.json` newest-first with the first user message as the title. `◀ ▶` cycles. Selecting one calls the same code path as `--resume <id>` and lets Roman continue typing. This is the "pick up where I left off" feature. |
| **Search** | Preset question launcher | A group window of sub-icons, each a saved phrase. Default presets: *Time in Japan*, *Time in New Mexico*, *Time in Portsmouth NH*, *Weather here*, *Latest news*. Clicking runs the phrase through `Agent.turn()` — deterministic intents from doc 05 (`local_time`, `open_target` with a Google URL) mean most presets never touch the model. **"+ New preset"** lets Roman type a phrase and choose *Ask TZ* vs *Open in browser*. Stored in `config/tz.local.json` → `ui.presets`. |
| **Browser** | Nothing in-window | Opens the real default browser to Google (or a URL typed in a tiny dialog). Roman's point about address-bar AI. |
| **Files** | Workspace listing | Wraps `list_files` / `file_read` for the workspace. File Manager look (tree on left, files on right, like the screenshot). Read-only in v1. |
| **Settings** | Control Panel look | Wallpaper (solid color, or an image file from the workspace), passcode/label, default model, routing (AUTO/MANUAL), "ask to open UI" behavior, startup chime. Writes `config/tz.local.json`. |
| **Clock** | Tiny always-open window | Local time; doubles as a demo that windows work. Nostalgia. |

Later ideas Roman may like: **Team** (the `/team` subagent receipts as a "Print Manager"-style queue), **Models** (a "Reversi"-sized window that lists Ollama models with sizes vs VRAM), **Notepad** (file_write into the workspace), **Recorder** (macro = ordered list of presets).

### 5. Window behaviors (v1 scope)

- Open, close, drag, minimize-to-icon, bring-to-front on click, remember last position per window in `localStorage`.
- Chat window streams tokens as they arrive (the terminal already streams; the UI mirrors that).
- Tool activity shows as the same `[tool] …` lines, in a monospace block, so nothing is hidden from Roman.
- Confirmations (`run_command`, destructive actions) pop a Win3.x message box with Yes/No — same `confirm` callback the terminal uses.

## Out of scope (explicitly)

- Real virtualization, a real file system, running arbitrary programs inside the window.
- Replacing the terminal. Roman said keep it.
- Mobile layout. This is a desktop toy for a desktop.
- Cloud anything.

## Open questions for Roman (decide when building)

1. Browser tab or native window? (Doc 07 recommends browser tab for Phase 1, pywebview later if he wants a real app icon.)
2. Win 3.1 (no taskbar, minimize-to-icon) or Win 95 (taskbar + Start button) — the "Start" icon name pulls both ways. Default: Win 3.1 chrome with a Win95-style bottom status strip.
3. Should closing the desktop window end the session? Default: no.
4. Wallpaper: solid color only in v1, image files in v1.5?
