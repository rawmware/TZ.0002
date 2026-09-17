# TZ — Hardware panel + chat presentation (implemented)

**Date:** 2026-09-17 · **Spec:** `TZ-UX-HANDOFF-2026-09-17.md`
**Touched:** `app/tz_terminal.py`, `app/tz_agent.py`, `tests/test_terminal.py`
**No new dependencies.** `requirements.txt` is unchanged.

---

## 1. Hardware

`Hardware` now has two surfaces that are kept apart on purpose.

- **Live load** — the background thread, unchanged. `/hardware` prints it
  through `terminal.emit`, labelled `[live load]`. It is also the bottom row
  of the prompt toolbar and of the ACTIVE block while the model is thinking.
- **Specs** — `Hardware.specs()`, a static inventory sampled **once** (no
  polling) and cached. `Terminal.specs()` renders it as a two-column Rich
  panel titled *This machine*, printed under the header at startup.

Rows: CPU model + physical cores / logical threads + clock, memory total,
GPU name + VRAM + driver, OS, Python, free disk on the workspace drive,
Ollama version + endpoint, loaded model, and **where inference is actually
executing** (derived from `/api/ps` `size_vram` vs `size`).

New/changed commands:

| Command | Behavior |
|---|---|
| `/specs` | Re-samples and reprints the panel |
| `/hardware` | Live utilization line, labelled, through `emit` |
| `/status` | Identity + model + routing + runtime + workspace + session **and** the specs panel |
| `/verbose` | Toggles `[route] [model] [usage] [tool] [waiting]` lines |

### Degrading honestly

- **No psutil** — the CPU and Memory rows say
  `psutil not installed - run: pip install -r requirements.txt`; every other
  row still works.
- **Non-NVIDIA GPU** — the name comes from `Win32_VideoController` via CIM and
  the row is marked `utilization not exposed (nvidia-smi only)`.
- **No GPU found at all** — `not detected`, never a zero.
- **Ollama down** — `version unavailable (is Ollama running?)`, and Inference
  says no model is resident yet.

Nothing is ever invented. Every probe is loopback-only or a local command, run
windowless (`CREATE_NO_WINDOW`) and wrapped so a failure returns `None` rather
than raising into the REPL.

## 2. Chat presentation

### Input

`PromptSession(multiline=True, wrap_lines=True, …)` with explicit key
bindings: **Enter submits**, **Alt+Enter / Ctrl+J insert a newline**. A long
prompt now wraps *downward* instead of sliding its own beginning off the left
edge — that was the "point where I can't see what I'm writing".

The private `session.layout.container.children[0].content.height = 6` poke is
gone. The toolbar is forced to **one row** (the second GPU line was pushing the
input area up on short windows) and grows a character counter past 120 chars.

### Streamed replies

The Live region no longer owns the response. It holds **only** the fixed
two-row ACTIVE block (elapsed, routing, live load, Ctrl+C). The reply prints
*above* it, one completed line at a time, straight into real scrollback — so
a printed line never moves again. A 200-line answer scrolls like ordinary
terminal output.

The reply is framed by rules (`AI · <model>` … closing rule) instead of a Panel
that has to be redrawn whole, and there is a blank line between turns.

### Formatting

Rather than re-rendering the finished reply as Markdown — which would reprint
lines the user has already read, the exact defect being fixed — TZ highlights
**as it commits**: a fenced code block is buffered until its closing fence and
then printed once as a syntax-highlighted panel; heading lines print bold;
everything else stays plain. Streamed text keeps `markup=False`, so model
output can never inject Rich markup. The text column is capped at 100 chars.

On Ctrl+C mid-stream the partial reply keeps its frame and the closing rule
reads `- canceled, unverified`.

## 3. Preserved

Tools, workspace write protection, confirmations, sessions under `data/tz/`,
routing (`/auto` `/fast` `/code` `/use`), OpenCode handoff, loopback-only
inference, and the plain-`print` path when `self.enabled` is False.

## 4. Tests

`tests/test_terminal.py` — 16 tests, all green, alongside `tests/test_tz.py`
and `tests/test_astra.py`:

- specs panel renders with psutil absent
- specs never invent a GPU reading
- long multiline input is echoed in full
- a 200-line reply commits each line exactly once
- a finished code block is highlighted without reprinting
- cancel marks the partial reply
- toolbar stays one line
- `/verbose` hides only detail tags
- help and specs stay plain when redirected (non-TTY unchanged)
