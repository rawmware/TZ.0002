# Roman live debugger and FAST response fix

## Installed location and use

The active `roman` launcher is `C:\Users\rjcot\AppData\Local\TZ\bin\roman.cmd`, which starts `C:\Users\rjcot\TZ.0002\Start-RAWM.ps1`. The TIZI workspace contains an older implementation and is not the active launcher target.

Exit an already-running Roman session with `/exit`, then run `roman` again to load the changes. Activity is visible by default in the same terminal.

- `/debug` or `/debug stats`: statistics and recent operation durations.
- `/debug off`: hide activity messages; telemetry continues locally.
- `/debug on`: show activity messages again.
- `/usage`: existing per-turn and session token usage.
- Esc or Ctrl+C during an operation: existing cancellation behavior remains.

## Diagnosis and fix

Observed Ollama logs showed Gemma3 1B taking about 18 seconds to load on the GPU and then spending excessive time processing the prompt. A direct GPU request took 7.34 seconds, of which 7.21 seconds was prompt evaluation for 11 tokens. A CPU comparison took 2.67 seconds including 2.25 seconds loading, with 0.18 seconds prompt evaluation for 27 tokens. These are individual measurements, not a controlled benchmark. The underlying GPU/runtime defect has not been diagnosed.

`config/settings.local.json` now sets `models.fast.numGpu` to `0`. This machine-specific configuration is gitignored: preserve it when moving or reinstalling the app. The CODE model remains as configured.

Streaming Ollama chat now uses `/api/chat`, passing the configured context size, output limit, temperature, optional per-model GPU setting, disabled thinking, and a ten-minute keep-alive. Native NDJSON response parsing preserves streaming, cancellation and token accounting and records Ollama timing measurements. Non-Ollama backends retain the existing SSE path. Nonstreaming planner/code-draft requests still use the existing compatible endpoint; the FAST CPU override applies to streaming chat.

## Activity and statistical coverage

`app/RAWMDebug.ps1` provides visible request start, selected model/route, message count, HTTP headers, first output token, completed/failed responses, operation starts, plan/tool status, and tool elapsed time. Existing five-second wait messages remain visible during blocking operations. Output continues streaming while the model responds.

`/debug` reports completed and failed/canceled responses, average latency, nearest-rank p95 latency, output token totals, tool outcomes, the last native runtime load/prompt/generation durations and generation token rate, plus recent bounded-operation durations. Each completion also displays first-token latency, input/output token counts and end-to-end output tokens per second. Generation speed and end-to-end speed have separate labels because loading and prompt processing affect the latter.

Statistics cover the last 1,000 telemetry events in the current process, not all historical sessions. A p95 based on a small sample is not a performance guarantee. Operation-ended events describe elapsed time and do not claim success. Agent statuses retain the distinction between verified local results, browser launch only, and unverified worker reports. External worker internal steps and hidden model reasoning are not available; the display reports observed execution boundaries and waits.

Local JSONL logs: `data/debug/activity-<PID>.jsonl`. Each process rotates its log after 5 MiB to one `.previous` file. Files from older processes remain available for diagnosis. Records contain metadata, counts and durations; this telemetry does not include prompts, generated text, file contents or tool arguments. Existing agent audit records are separate. Diagnostic file-write failures do not interrupt actions.

## Files changed

- `app/RAWM.psm1`: native streaming, response telemetry, `/debug`, startup/help text.
- `app/RAWMRuntime.ps1`: shared operation timing and wait telemetry.
- `app/RAWMAgent.ps1`: agent event visibility and tool durations.
- `app/RAWMDebug.ps1`: telemetry, display and statistics.
- `config/settings.local.json`: FAST CPU setting, local/untracked.
- `tests/Test-RAWMDebug.ps1`: statistics, bounded event retention, JSONL and optional live test.

## Verification

- Actual installed `roman.cmd`, piped `hello?`, `/debug`, `/exit`: greeting completed in 1.95 seconds, first token in 1.92 seconds; 320 input / 3 output tokens, visible diagnostics and statistics.
- `tests/Test-RAWMDebug.ps1 -Live`: passed; subsequent real greeting completed in 0.68 seconds with token usage and native timing records.
- `tests/Test-RAWMReliability.ps1`: all 61 checks passed after changes, including timeout, cancellation and stopping owned worker subprocesses.
- `tests/Test-RAWMInterface.ps1`: all 3 checks passed.

No live CODE-model generation or external-worker provider run was performed. Reliability tests exercise worker lifecycle with test helpers. If a future hang occurs, retain that process's JSONL file and Ollama server log and compare the last recorded phase. These changes are installed in the working tree and have not been committed.

## Reversal

Remove `numGpu` from the FAST entry to restore automatic GPU selection for chat. Revert only the changes described above to remove telemetry/native streaming; do not discard unrelated future changes. Restart Roman after configuration or code changes.
