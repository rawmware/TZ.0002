# Terminal redesign — implementation and continuation notes

## User intent and scope

The user wants the command prompt to feel like talking directly to their computer:
technical and futuristic, but calm and easy to read. Preserve a clear distinction
between their words, the assistant's name, and the actual responding model. Preserve
working tools, safeguards, launch aliases, sessions, workspace boundaries, and previews.

The original request mentioned a handoff, then explicitly clarified: **you are the
builder**. This work implements the changes. This file records the result for any
future developer/model; it is not an instruction to adopt a particular model identity.
“Astra” referred to an external development model, not a product name or app backend.
The attached readME2.MD supplied visual feedback; the attached downloads/AGENTS.md
supplied execution preferences. Neither document's examples override the user's
current request or establish that routing was actually broken.

## What changed

- `app/tz_terminal.py`: framed header and user input, separate `Me` identity,
  assistant label from the existing passcode setting, restrained status colors,
  colored workspace path, compact live resource bars and values. Response text remains
  plain and readable. No fake processing delays or invented telemetry.
- Live sampling runs independently of input and inference. CPU and RAM use psutil;
  GPU and VRAM use nvidia-smi with a bounded timeout and hidden Windows subprocess.
  Unavailable GPU data displays n/a. Unsupported terminals retain the plain interface.
- `app/tz_agent.py`: actual `/auto`, `/fast`, `/code` routing, transparent route reasons,
  model metadata, manual selection precedence, and opt-in diagnostics. Empty small-model
  answers can fall back once to the task model. Routing preferences survive session saves.
- `app/tz_opencode.py`: assistant identity and configured-model labeling, without the
  repeated completion box. Existing execution and permission behavior remains intact.
- Added Rich, prompt_toolkit, and psutil requirements and focused regression tests.

## Routing finding

The older PowerShell runtime has automatic routing; the current Python entry point
previously had one selected Ollama model plus coding-task dispatch to OpenCode. The
Python port had not carried over the small-versus-task model routing. This was not
evidence of a broken Ollama router.

The new router is deliberately conservative: a short opening greeting or basic question
can use a small installed model; context-bearing follow-ups and tasks use the existing
task model. The installed defaults tested here are gemma3:1b and tz-agent:latest, whose
runtime metadata identifies Qwen3 4B Q4_K_M. Qwen version numbers from the user's example
were illustrative, not requests to invent or download models. Larger installed models
are selectable with `/use`; they are not automatically loaded for every complex prompt.

## Verification

- 28 Python tests passed, including the existing workspace, write protection, preview,
  OpenCode error, cancellation deadline, and truncated-stream checks.
- New tests cover model selection, manual pinning, missing-model fallback, empty-answer
  fallback, quiet diagnostics, plain redirected output, real prompt rendering/input,
  and preservation of streamed text when canceled.
- Live Ollama smoke checks produced a greeting from gemma3:1b and a greeting from
  tz-agent:latest. Gemma needed the legacy CPU workaround and a chat-only system prompt;
  both fixes were verified against the running runtime.
- Live hardware sampling returned actual CPU/RAM and GPU/VRAM readings on this machine.
- Interactive PTY checks exercised framed input, resource refresh, streamed greeting,
  and clean exit. This automated terminal supplies TERM=dumb by default, so interactive
  visual checks used TERM=xterm-256color only in their test processes.

## Limits and next-person guidance

GPU monitoring currently supports nvidia-smi. Other GPU vendors show n/a; CPU/RAM
continue working. Samples represent the whole machine. Telemetry is inactive in
noninteractive one-shot mode. No graphical screenshot comparison was performed.
The legacy PowerShell runtime was left unchanged. This work targets `tz.py` / `TZ.cmd`
and aliases registered through the current Python installer. Restart existing app
processes to load the changes. Keep any future routing expansion evidence-based and
avoid losing tool support, context, or local-only restrictions for visual effect.
