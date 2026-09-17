# Qwen worker investigation and agent optimization

Investigation and implementation plan — 2026-09-16. Documentation only; no model benchmark or code fix was performed.

## Correction after reading the supplied transcript

Primary evidence is now `D:/COMPSCI-RESEARCH/Html's/ollama test.md`. The initial investigation inspected an older/different `rom.ps1`; it did not inspect the application that produced this transcript. Earlier code findings below remain true only of that prototype. In particular, disabled streaming and its 900-second HTTP timeout cannot be identified as the cause of the newer worker's 300-second timeout.

The transcript shows a Qwen worker approved to create an exploding-letter HTML program and open Notepad. It prints elapsed-time messages roughly every five seconds, then stops after 300 seconds with “No completion was verified.” This is a five-minute timeout, not a completed three-minute task. No file path, actual tool event, process output or completion artifact appears in the supplied record.

It also shows session IDs, `/resume`, `/export`, multiple worker backends, cancellation instructions and approval plans. These features exist in the displayed interface; whether their implementation works correctly still requires testing. The exact worker executable, model, endpoint, working directory, exit code and logs are absent. Do not identify this worker with the locally installed `qwen3.6:latest` merely because both names contain Qwen.

## What the transcript establishes

| Observation | Finding | What remains unknown |
| --- | --- | --- |
| Repeated elapsed-time messages until 300-second timeout | Worker visibility is insufficient despite a responsive heartbeat | Whether it generated, ran tools, waited for input, retried, or stalled |
| Explicit warning that final worker report is unverified | The UI already acknowledges a verification gap | Whether files or desktop actions occurred |
| Problem-solving prompts repeatedly show FAST / `gemma3:1b` | Routing did not visibly escalate these reasoning tasks | Router implementation and escalation policy |
| Collatz answer copies sample, then claims `3*3+1=9` | Intent recognition and arithmetic correctness fail | Whether a capable alternate model would pass on this hardware |
| Apples/oranges response confuses fruit categories | Fast answers are not reliably correct | Extent of context contamination versus base model limitations |
| Jake rewrite invents regional concerns and changes ownership | Rewrite fidelity fails | Prompt/template contribution |
| One response is empty; another ends at 384 output tokens mid-answer | Need explicit empty/truncated-result handling | Actual generation limit and finish reason |

The transcript's token rates are displayed application metrics whose calculation has not been inspected. Do not use them as verified end-to-end throughput or infer a hardware bottleneck from them.

## Investigate the actual worker first

1. Resolve what `roman` and `rom` launch in the relevant PowerShell session, including alias/function definitions and executable paths. Record version and source location. Do not replace the working launcher with the older prototype.
2. Locate the supplied session and worker run records using session IDs, timestamps and the exact HTML prompt. Determine whether stdout/stderr, plans or artifacts already exist before adding another logger.
3. Inspect Qwen worker configuration without printing secrets: executable and arguments, cwd, model ID, endpoint host, authentication method and environment variable names. If the backend requires a key or paid service, exclude it under the user's existing policy; do not obtain credentials to reproduce it.
4. Capture process start, first output, tool events, exit code and child-process lifecycle. Check for an interactive approval/login prompt hidden behind redirected output, buffering, dependency failure, retries or an unexpected working directory.
5. Reproduce in an isolated workspace using an eligible backend. First ask it to write one tiny text file, then generate the HTML, then open Notepad. This separates worker startup, generation, filesystem actions and desktop automation.
6. Test timeout and cancellation with a controlled fixture. Preserve partial-output evidence and verify termination of task-owned children without stopping unrelated model services.

These are pending diagnostic steps, not actions already performed. An elapsed timer is evidence that the supervising UI is alive, not that the child worker is progressing.

## Worker result contract

Every worker should return a run ID, status, model/provider provenance, actual action receipts, changed file paths, validation results, error/exit details and the next recovery step. Link raw local logs for diagnosis and show a concise user-facing account. Distinguish worker-reported success from independently verified success.

For this HTML task, verify the file exists and inspect its contents; open it in a browser and check the animation; verify the separate Notepad operation if requested. If only HTML generation succeeds, report that partial result. At timeout, list discovered artifacts as unverified when validation has not occurred. Do not claim that no files changed solely because the worker timed out.

Automatically produce a completion/handoff Markdown for implementation tasks, including timeout and partial-failure outcomes, following the convention in the architecture document. Keep that report discoverable from the run's final message.

## Quality-aware routing before more agents

Keep fast rewriting on a lightweight model only if it preserves meaning. Route programming problem statements and multi-step reasoning by intent and conversation context, not only keywords. A user correction such as “think deeper” should trigger explicit reevaluation, with an eligible stronger model when available, rather than another confidently wrong fast answer.

Score latency together with correctness, rewrite fidelity, artifact completion and recovery behavior. Use the companion document's transcript regression cases as the initial quality suite. Do not launch multiple agents for a small HTML page until one worker can complete it reliably and visibly.

## Older prototype findings — separate evidence

The available implementation has definite visibility gaps and plausible latency contributors. It does not contain a persistent worker scheduler or an autonomous tool-execution loop. Its normal turn is a model request followed by parsing optional file actions. Calling this a worker does not establish that it spent three minutes editing or testing anything.

The supplied transcript now provides the task prompt, surrounding session context and elapsed-time sequence, but no internal worker trace. The older code alone cannot reconstruct this run. The sections below are retained as prototype improvement candidates, not a root-cause finding for the transcript application.

## Observed local state

Read-only requests to the local Ollama service succeeded. `/api/ps` returned no loaded models at inspection time; this does not establish residency during the reported run. Installed models from `/api/tags`:

| Model | Reported parameters | Quantization | Stored size, approximately |
| --- | --- | --- | --- |
| `gemma3:1b` | 999.89M | Q4_K_M | 0.76 GiB |
| `gemma4:26b` | 25.2B | Q4_K_M | 17.33 GiB |
| `qwen3.6:latest` | 36.0B | Q4_K_M | 22.29 GiB |

Windows reported about 31.85 GiB physical RAM. Stored model size is not total inference memory: context cache, engine overhead and other applications also need memory. GPU model/VRAM and actual offload were not established. Thus CPU offload, paging and memory pressure are hypotheses, not measured causes.

## Findings in the code

Line numbers refer to `rom.ps1` as inspected; function names are the durable anchors.

| Evidence | Consequence | Confidence |
| --- | --- | --- |
| `Invoke-RomOllama`, lines 381–443: `stream = $false` | User sees no partial response during generation | Confirmed |
| Main loop, line 841: only “Thinking...” before blocking request | Cannot distinguish loading, generation or failure while waiting | Confirmed |
| HTTP timeout is 900 seconds | A request may appear inactive for up to 15 minutes before timeout | Confirmed |
| Request options set temperature only | No application-level output/context budget or explicit thinking policy | Confirmed; engine defaults still apply |
| `Resolve-RomModel`, line 275: name-pattern routing | Code selection can choose a large Qwen without checking memory or speed | Confirmed mechanism; actual historical route unknown |
| Installed Qwen is `qwen3.6:latest`, 22.29 GiB stored size | Large local workload relative to available system RAM | Observed; performance effect unmeasured |
| `Invoke-RomCouncilTurn`, line 462: sequential unique candidates then synthesis | Two or three generation calls per turn, potentially switching large models | Confirmed |
| Main loop retains messages; council serializes history and repeats current request | Growing context and duplicated current prompt add avoidable input | Confirmed |
| `LoadDurationMs` captured but not shown; prompt/eval durations discarded | Cannot separate model loading, prompt processing and generation costs | Confirmed |
| No durable run/event history in inspected files | Afterward, console text is the main evidence; restart loses in-memory session | Confirmed |
| Empty answer falls back to `message.thinking` | Internal generation text can be mistaken for a finished deliverable | Confirmed |
| Actions execute only after model response; no general test runner or file-reading tool | “Working” can mean generating text, with zero verified project work | Confirmed |

Also, the README's “smallest model by default” is conditional: the resolver first uses an exact configured model if installed. The current inventory includes the default `gemma3:1b`. Do not infer a selected model from the README alone.

## First fixes: visibility and truthful completion

1. Create and persist a run record before dispatch: run ID, exact model/digest, engine, route reason, task goal and budgets.
2. Implement streaming with separate answer text and phase events. Do not expose raw internal reasoning as an activity log. Report tool events only when the tool actually runs.
3. Add queued/loading/generating/tool-running/verifying/terminal states. Where engine telemetry cannot distinguish loading from generation, say “waiting for engine response.”
4. Show elapsed time and last real event. After a configurable inactivity threshold, display a stalled warning and offer Stop; elapsed time is not percentage complete.
5. Persist each file action receipt immediately. Use atomic writes and record partial failure if a later action fails.
6. End with: outcome, actual changes, checks and their results, unfinished items, elapsed time and artifact links. A text-only run must say “No files changed; no checks run” when applicable.
7. Support cancellation and retain cancelled/interrupted records. UI acknowledgement and confirmed backend stop are different events; keep tracking if the backend cannot cancel immediately.

The Ollama chat API exposes streaming and timing fields useful for this instrumentation. [API documentation](https://docs.ollama.com/api/chat).

## Measure before blaming or replacing Qwen

Use a disposable workspace. First capture exact runtime/model versions, model digest, RAM/VRAM, active processes, context settings and the prompt that reproduced the problem. Inspect `ollama ps` during inference to establish CPU/GPU placement; it cannot reconstruct a past run. [Ollama diagnostics](https://docs.ollama.com/faq).

Benchmark three tasks: a three-bullet explanation, a small code function with known expected outputs, and saving a specified file with exact content. Use the same prompt, bounded context and output allowance across comparable models. Score correctness and actual artifact creation, not merely completion time.

For each eligible installed model, run one controlled cold sample and five warm samples with council off. Do not unload a model used by another active task. Repeat council separately only after single-model measurements. Report medians and ranges; five samples are insufficient for a reliable tail-percentile claim.

Record client wall time, first answer latency, server load duration, prompt-evaluation duration/count, generation duration/count, peak RAM/VRAM if measurable, tool duration, final answer validity and artifact correctness. Preserve raw measurements locally with run IDs. Compute generation tokens/second only when evaluation duration is positive; mark unavailable fields as unknown, not zero.

Interpretation:

- High load time, faster warm repeats: investigate residency/model switching.
- High prompt-evaluation time: reduce irrelevant history and duplicate context.
- Low generation throughput with CPU placement or paging: evaluate a smaller compatible model/context.
- Long reasoning with little usable answer: test supported lower-thinking settings and output limits.
- Fast generation but absent deliverables: fix tool/action handling and success verification.
- Slow council only: remove unnecessary passes; do not assume parallelizing large models will help.

## Optimize worker selection and agent use

| Priority | Proposed change | How to validate |
| --- | --- | --- |
| P0 | Streaming, event history and outcome receipts | Every long run is inspectable during execution and after restart |
| P0 | Enforce no-key/no-paid/local execution policy | Block incompatible routes before any request, including retries |
| P1 | Default to one capable worker; council opt-in | Compare successful-task latency with baseline |
| P1 | Set task-specific output, context and time budgets | No silent indefinite run; truncation is labelled incomplete |
| P1 | Route by capability and measured hardware fit | Smaller model chosen where it meets quality targets; explicit model choice respected |
| P1 | Bound history; retain requirements and relevant evidence | Same task correctness with less prompt processing |
| P1 | Remove duplicated council prompt; review only when useful | Fewer calls/tokens without losing required validation |
| P2 | Evaluate local NVIDIA models through eligibility gates | Offline, keyless completion and measured benefit before adoption |

Initial tuning experiment: simple answers up to 256 output tokens; small code tasks up to 1,024; interactive work budget 60 seconds. These are adjustable experiment settings, not limits to impose blindly on every task. Larger tasks need a visible task budget and checkpoints. A timeout must not silently relaunch the same heavy request.

Thinking controls vary by model/runtime. Test capability support before requesting a setting; do not assume every Qwen model accepts identical switches. A faster setting is acceptable only if task correctness remains adequate.

For future multi-agent work, every agent needs one bounded deliverable, relevant context, allowed tools, a deadline and an artifact receipt. The coordinator must explain why delegation is needed and show each worker's status. Share file ownership explicitly; serialize conflicting edits. Begin with one inference slot, expanding concurrency only after measurement.

Retry at most once for a classified transient failure. Never repeat side effects blindly, silently upgrade to a paid/cloud model, or treat a reviewer agreeing with an answer as equivalent to an executed test.

## Completion criteria

- All runs have inspectable outcomes and actual action evidence; restart preserves history.
- No three-minute run leaves the user with only a spinner or “Thinking...”.
- The controlled simple warm task meets the companion test plan's first-answer target, or reports why the reference hardware cannot meet it.
- Optimization lowers median successful-task latency on the measured baseline without reducing correctness; retain raw before/after data.
- No claim that Qwen itself is defective without reproducing and separating model, hardware, routing and orchestration effects.

Immediate order for the transcript application: identify the actual launcher and worker implementation, recover existing evidence, instrument missing worker events, verify cancellation, run quality/performance regressions, then improve routing and generation budgets. Apply older-prototype changes only where the actual implementation has the same issue. Adding many models first would make the current visibility problem harder to diagnose.
