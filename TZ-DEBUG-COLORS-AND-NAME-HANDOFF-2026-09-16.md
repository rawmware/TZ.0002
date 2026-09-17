# TZ display name and colored live debugger — handoff addendum

## User-visible changes

The installed app's configured name is now **TZ**. The existing setting is called `interface.passcode`, but inspection confirmed it is a display name, not an authentication credential. It never meant that end users were communicating with the human owner. No access-password feature was added.

Restart the current app with `/exit`, then launch with the existing `roman` command. The banner, prompt, response heading, and exit message use TZ. The launcher command is unchanged.

- `/passcode`: show the current name and explain its meaning.
- `/passcode TZ`: set the name immediately and persist it across restarts.
- `/passcode My App`: names may contain spaces.
- Names accept 1–32 letters/numbers/spaces/underscores/hyphens, starting with a letter or number. Invalid/control-character input is rejected.

Changes are written atomically to `config/settings.local.json`, preserving existing model/backend/worker settings. That local configuration is gitignored. The running setting changes only after a successful write.

The chat system instruction now uses the configured application name and explicitly distinguishes it from the human user's name. The behavior file no longer describes the app as “Roman's local assistant.” Resumed chats receive the refreshed system instruction, though their historical messages remain unchanged.

## Debug appearance

Every visible activity line has a red **●** beside **LIVE DEBUG**. Stage colors:

| Color | Meaning |
| --- | --- |
| Cyan | Request/response stages and active debug marker |
| Green | Completed responses or verified results |
| Amber | Agent actions, tools, waits and reported/launched outcomes |
| Red | Errors/failures |
| Gray / white | Metric names / values |

ANSI codes are emitted outside the wrapping calculation and reset before model text. The red dot indicates debug activity, not an error by itself. Startup, `/debug on`, and `/debug` show the marker. `/debug off` hides live lines while keeping local telemetry, as before. Five-second wait messages use the colored debug format while enabled; cancellation guidance remains available when disabled.

## Verification

- 15 interface checks passed, including immediate change, persistence/reload, preservation of model settings, valid spaces, rejected inputs and no disk mutation on rejection.
- Debugger regression test with real Ollama greeting passed (2.33 seconds in this run).
- All 61 reliability checks passed, including worker cancellation and timeouts.
- The actual installed launcher was used to set TZ via `/passcode TZ`; a fresh process was used to inspect the saved name, generate a greeting, and toggle debug off/on.
- `git diff --check` passed.

## Observed but unresolved model behavior

The supplied transcript contains one empty model response and one inappropriate refusal to “waht is happening.” The subsequent retry answered. These are recorded as unresolved model behavior; the UI/name changes do not claim to fix them. There is no automatic replay of tool actions or silent model substitution.

## Changed files for this addendum

- `app/RAWMDebug.ps1`: red dot and semantic stage/metric colors.
- `app/RAWMRuntime.ps1`: consistently marked wait messages.
- `app/RAWM.psm1`: persisted `/passcode` command, help, current-name system instruction and marked debug startup.
- `context/RAWM-BEHAVIOR.md`: remove hard-coded human-owner identity.
- `tests/Test-RAWMInterface.ps1`: persistent-name checks in an isolated fixture.
- `config/settings.local.json`: local display name TZ; FAST CPU setting preserved.

Previous changes remain uncommitted. This addendum accompanies `ROMAN-DEBUGGER-WARM-HANDOFF-2026-09-16.md`; it does not replace the earlier runtime diagnosis and limitations.
