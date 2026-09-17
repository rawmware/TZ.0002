# TZ — UX Change Request: Hardware Panel + Chat Presentation

**Author:** Roman (RawmWare) · **Date:** 2026-09-17
**Scope:** `app/tz_terminal.py`, `app/tz_agent.py` (+ tests)
**Status:** Implemented — §1, §2.1-2.3, §2.5 in `docs/TZ-UX-HARDWARE-AND-CHAT-2026-09-17.md`; §2.4 persistent status line and the `/team` subagents in `docs/TZ-TEAM-SUBAGENTS-2026-09-17.md`.
**Repo:** https://github.com/rawmware/TZ.0002 — **all changes must land there.**
See §5; read it *before* writing code, not after.

---

## 0. Warm handoff — read this first

TZ is a local, provider-neutral agent CLI (Ollama backend, OpenCode for coding
tasks) intended to eventually ship to other people. The terminal layer was
rebuilt on 2026-09-17 (see `docs/TZ-TERMINAL-BUILD-2026-09-17.md`): Rich for
output, prompt_toolkit for input, psutil + nvidia-smi for live telemetry.

Two things are not working for the user:

1. **The app never tells you what machine it's running on.** There is live
   *utilization* telemetry, but no *specs*. As a gamer/creative coder, Roman
   wants the "here's your rig" moment — the thing that makes local inference
   feel earned rather than abstract.
2. **The chat is unreadable.** Text scrolls continuously, the line above
   disappears, and while typing there is a point where the user can no longer
   see what they are writing. Responses are not visually contained.

Everything below is a change request. Preserve existing behavior not named
here: tools, workspace write protection, confirmations, sessions under
`data/tz/`, routing (`/auto` `/fast` `/code` `/use`), OpenCode handoff,
loopback-only inference, and the plain-text fallback for dumb terminals.

---

## 1. Hardware: show me my specs

### 1.1 What's wrong today

`Hardware` in `app/tz_terminal.py` only samples **live load**:

```
CPU [||......] 24%  |  RAM 12.3/32.0 GB  |  GPU0 [|.......] 8%  |  VRAM 1.2/8.0 GB
```

That string is the *only* hardware surface, and it appears in two places that
are easy to miss:

- `bottom_toolbar` of the prompt — a single line at the very bottom, overwritten
  and easy to lose (issue #2 makes this worse).
- the `activity()` Live panel — only visible while the model is thinking.

There is **no static inventory anywhere**: no CPU model name, no core/thread
count, no GPU name, no total RAM at rest, no OS build, no disk, no Python
version, no Ollama version. The header panel prints label, model, workspace,
and a help line — nothing about the machine.

Additional defects found while reading the code:

- `/hardware` in `main()` uses bare `print()`, bypassing the Rich console — so
  it renders outside the styled layout. Same for `/help`, `/status`, `/tools`,
  `/models`, `/use`, `/clear`, and the KeyboardInterrupt / `[incomplete]`
  handlers. **All of these should go through `terminal.emit`.**
- If `psutil` is missing, `Hardware.run()` sets a one-line message and returns
  forever — telemetry is silently dead for the rest of the session with no
  actionable prompt.
- GPU support is nvidia-smi only. AMD/Intel/Apple show `n/a` with no
  explanation of *why*.
- `system_info` (the agent tool, `tz_agent.py:344`) already returns OS, Python
  and program paths. That data exists and is never shown to the user.

### 1.2 What I want instead

**A. A specs panel at startup**, printed once under the header. Static
inventory, gathered once, no polling:

| Row | Source |
|---|---|
| CPU model, physical cores / logical threads, base clock | `platform.processor()` on Win via `platform.uname()`; better: `psutil.cpu_count(logical=False/True)`, `psutil.cpu_freq()` |
| RAM total | `psutil.virtual_memory().total` |
| GPU name + total VRAM + driver | `nvidia-smi --query-gpu=name,memory.total,driver_version`; fall back to WMI `Win32_VideoController` on Windows so AMD/Intel still get a **name** |
| OS + build | `platform.platform()` |
| Python | `sys.version.split()[0]` |
| Disk free on workspace drive | `shutil.disk_usage(workspace)` |
| Ollama version + endpoint | `GET /api/version` on `self.base_url` |
| Loaded model + its param size / quant | already computed in `local_model()` → `model_description` |
| Inference device | "GPU (CUDA)" / "CPU" — derive from `/api/ps` `size_vram` vs `size` for the loaded model |

Style it like the existing header: Rich `Panel`, cyan border, two columns
(label left, value right) so it reads as a spec sheet, not a log line.

**B. `/specs` — a new command** that reprints that panel on demand.
Keep `/hardware` for the live utilization line, but route it through
`terminal.emit` and label it clearly ("live load" vs "specs").

**C. Merge specs into `/status`.** `/status` should be the single "what am I
running" answer: identity, model, routing, runtime, workspace, session id, and
the hardware block.

**D. Make the live telemetry actually visible.** See §2.4 — it belongs in a
persistent status line that never gets eaten by scroll, not only in the
bottom toolbar.

**E. Degrade honestly, never silently.** If psutil is missing, say
`psutil not installed — run: pip install -r requirements.txt` in the specs
panel where the numbers would be, and keep the rest of the rows working.
If the GPU vendor isn't nvidia, show the GPU **name** from WMI and mark
utilization `not exposed (nvidia-smi only)`. Never print an invented value.

**Explicit non-goal:** don't replicate the browser-style dump Roman pasted
(WebGPU adapters, WASM threads, origin storage). That was an example of the
*feeling* — "the app knows my machine" — not a spec list. Keep it to what a
local LLM runtime actually cares about: CPU, RAM, GPU/VRAM, disk, and where
inference is executing.

---

## 2. Chat presentation: I can't see what I'm writing

### 2.1 Why the input disappears

In `Terminal.__init__`:

```python
self.session = PromptSession(erase_when_done=True, show_frame=True,
    reserve_space_for_menu=0, style=...)
self.session.layout.container.children[0].content.height = 6
```

- `multiline` is **not enabled**, so a long prompt scrolls **horizontally**
  inside one row. Past the terminal width, the beginning of your own sentence
  slides out of view — this is the "point of text where I can't see what I'm
  writing."
- The hard-pinned `height = 6` reaches into prompt_toolkit's private layout
  tree. It reserves rows whether or not they're needed, and it is fragile
  across prompt_toolkit versions.
- `bottom_toolbar` renders the hardware string with an embedded `\n`, so the
  toolbar takes two rows and pushes the input area further up on short windows.
- `erase_when_done=True` wipes the input region, then `read()` reprints the
  text as a `Me` panel — so the input visually jumps position on submit.

**Fix:**
- `PromptSession(multiline=True, wrap_lines=True, prompt_continuation=…)`,
  with **Enter = submit** and **Alt+Enter (or Ctrl+J) = newline** bound
  explicitly via `KeyBindings`, so long prompts wrap downward and stay readable.
- Drop the private `layout.container.children[0]` poke. Let the input grow
  naturally; cap it with a `max` height if needed through supported API.
- Keep the toolbar to **one** line; move the second GPU line into the status
  line from §2.4.
- Show a live character/token-ish counter in the toolbar for long prompts.

### 2.2 Why the response scrolls away

In `activity()`:

```python
with Live(console=self.console, get_renderable=render,
          refresh_per_second=2, transient=True) as live:
```

The whole streamed response is accumulated in `self.stream_buffer` and
re-rendered **as one growing Panel, every 500ms**. Rich `Live` can only own a
region that fits the screen. Once the reply exceeds the terminal height:

- Rich clips or repaints the region, so the terminal scrolls on every refresh
  — the user sees a constantly moving wall of text.
- Earlier lines are re-drawn at new positions instead of settling into
  scrollback, so "the line above" is never stable.
- `transient=True` erases the whole panel at the end, then `finally:` reprints
  the *entire* buffer as a fresh Panel — a full-height flash/duplicate at the
  end of every turn.

**Fix — stop streaming into a Live panel.** The correct pattern:

- The **Live region holds only the small, fixed-height status block**
  (elapsed time, model, route, hardware bar, "Ctrl+C cancels"). One to three
  rows, never grows.
- The **response text prints above it, normally, line by line**, as complete
  lines arrive. Committed lines enter real scrollback and never move again.
  Buffer partial tokens until a newline (or a soft-wrap width boundary) and
  then `console.print` that line.
- Frame the reply by **printing a header rule and a footer rule** around the
  streamed text (e.g. `console.rule("AI · <model>")` … `console.rule()`),
  instead of a Panel that must be redrawn whole. This satisfies "wrapped
  within a container" without fighting the scroll region.
  - *Optional alternative:* keep a real Panel but only for replies that fit
    under ~60% of terminal height; above that, fall back to ruled streaming.
    Decide with `self.console.size.height`.

### 2.3 Response formatting

Currently every reply is raw plain text through `console.print(..., markup=False)`.

- Render assistant output as **Markdown** once the turn completes (Rich
  `Markdown`), so headings, lists and **code blocks get syntax highlighting**.
  Stream plain during generation, then re-render the finished block. This is
  the single biggest readability win for a coding agent.
- Keep `markup=False` on the streaming path so model text can never inject
  Rich markup.
- Wrap at a readable measure — cap the text column at ~100 chars even on wide
  terminals, left-aligned.
- Add one blank line between turns. Right now `[model]`, `[route]`, `[usage]`,
  `[tool]` and reply text run together.

### 2.4 Persistent status line

Add a bottom status line that survives the whole session — model, route,
workspace basename, session id, and the live CPU/RAM/GPU bars. Implement as a
one-row Rich `Live` anchored at the bottom between turns, or reuse
prompt_toolkit's toolbar while reading. The user should be able to answer
"what's my machine doing right now" at any instant without running a command.

### 2.5 Smaller items

- `/help` should render as a Rich table through `emit`, not a bare `print`.
- Tag lines (`[route]`, `[model]`, `[usage]`, `[tool]`) should be dimmed and
  prefixed consistently, or collapsed behind a `/verbose` toggle — they
  currently compete with the answer for attention.
- On `KeyboardInterrupt` mid-stream, keep the partial reply framed and mark it
  `— canceled, unverified` rather than dropping a bare line.
- Preserve the non-TTY path exactly: when `self.enabled` is False everything
  must still be plain `print`. Tests in `tests/test_terminal.py` assert this.

---

## 3. Suggested order of work

0. **Set up the GitHub bridge first — §5.** Nothing below is finished until it
   is pushed to `rawmware/TZ.0002`.
1. Route every bare `print()` in `main()` through `terminal.emit`. (Cheap,
   unblocks consistent rendering for everything else.)
2. Build `Hardware.specs()` static inventory + startup panel + `/specs` +
   `/status` merge. (Self-contained, immediately visible win.)
3. Fix the input: `multiline=True`, `wrap_lines=True`, explicit key bindings,
   remove the private layout poke, single-line toolbar.
4. Rework `activity()`: small fixed Live status block, line-committed
   streaming above it, ruled container, no `transient` reprint.
5. Markdown + syntax-highlight the completed reply.
6. Persistent status line.
7. Tests: specs panel renders with psutil absent; long multiline input echoes
   fully; a 200-line streamed reply does not re-render previously printed
   lines; non-TTY output unchanged.

## 4. Constraints for the implementer

- Local only. No network calls beyond the loopback Ollama endpoint.
- No invented telemetry, no fake latency, no placeholder numbers.
- Windows is the primary target (`nvidia-smi` must stay windowless via
  `CREATE_NO_WINDOW`); don't break POSIX.
- Anything added to `requirements.txt` must be optional-degrading, matching the
  current psutil pattern.
- Run `tests/test_terminal.py` and `tests/test_tz.py` before handing back.
