# Testing TZ as a first-time user

Planning document — 2026-09-16. These are test instructions and proposed acceptance criteria, not completed test results.

## My goal

I want to open TZ, understand what it does, complete a useful task, see what happened, and return to my work without understanding model infrastructure. I must never need an API key or payment details.

The primary user-experience evidence is `D:/COMPSCI-RESEARCH/Html's/ollama test.md`. Its `roman` command differs from the older `rom.ps1` inspected in this workspace. The transcript already shows session controls, worker selection, approval and cancellation instructions. Use the actual installed build's `/help` when testing; do not substitute the old prototype's command syntax. Future screens and controls below remain proposed. Mark missing features as “not implemented,” not as passing.

## Replicate a new user without breaking my desktop or laptop

Use a disposable Windows virtual machine with a clean snapshot as the main onboarding environment. Keep the existing TZ installation, profile, engines, model directories and environment variables untouched. A new Windows account is a useful secondary test but may still see machine-wide services, so it is not proof of clean installation. VM inference speed is not representative of native GPU performance.

1. Prepare a clean VM with no TZ, no Ollama, no model weights and no provider accounts or keys. Record OS and resource allocation. Take a snapshot before installing.
2. Transfer only the candidate release installer and the test checklist. Do not mount personal folders or copy the developer profile. Permit the explicitly tested setup downloads.
3. Walk through download, install, launch, model acquisition and first successful answer. Record every manual dependency and confusing wait.
4. Test cancelled downloads, interrupted setup, retry, app update and uninstall. Revert the snapshot between scenarios instead of editing the working desktop installation.
5. Repeat with a preinstalled eligible engine/model to test reuse without configuration changes. Confirm uninstall preserves that external installation.
6. Measure real inference performance separately on native reference hardware with an isolated test workspace and app data directory. Do not stop shared model services while another task uses them.

The test setup is a plan; no VM, installation, download or reset was performed for these documents.

## Regression cases from the actual conversation

| Case | Test | Pass condition |
| --- | --- | --- |
| R01 | Type `clear`, then consult `/help` | Clear or explain the recognized command; do not silently treat a UI intent as successful clearing |
| R02 | Ask for a general solution to the supplied Collatz programming problem | Provide an algorithm and usable implementation, not merely the sample sequence; test `n=1`, `n=3`, and additional inputs with an independent oracle; use integer capacity adequate for intermediate values |
| R03 | Ask to reconsider the Collatz answer | Correctly calculate `3*3+1=10`; do not generate a longer incorrect trace |
| R04 | Repeat the apples/oranges problem | Under the natural assumption that all dropped oranges are recovered, answer 100 oranges and no intact apples; state any material ambiguity |
| R05 | Rewrite the Jake/Mexico message | Preserve friendship, playful tone, speaker ownership of the application and invitation; invent no claims about regional conditions |
| R06 | Rewrite the Britney desktop request | Preserve eight desktops, supply-chain delivery, pickup, reimaging and deployment responsibilities |
| R07 | Ask for more pay and less work respectfully | Preserve both requested goals; do not omit the compensation request |
| R08 | Correct the model after a name question | Respond to the correction; never count an empty answer as success |
| R09 | Say “think deeper” after a failed answer | Explicitly reevaluate and show any route change; do not stay on an unsuitable fast route solely because the follow-up is short |
| R10 | Ask for an HTML hello-world animation with exploding letters, saved and opened in Notepad | Verify created file/path and contents, verify Notepad action separately, and render the animation in a browser before claiming visual success |
| R11 | Simulate the Qwen worker reaching its 300-second limit | Report timeout plus known completed actions, partial files, logs and unverified items; verify no orphan process continues writing |

Repeat R02–R09 in both a clean session and the original conversation order to distinguish model quality, routing and accumulated-context effects. R10 requires separate evidence for code creation, editing application launch, and rendered behavior; success at one does not prove the others.

## Setup

- Use a new test workspace and disposable sample files. Do not use personal documents or overwrite existing work.
- Test both a clean Windows user environment and an environment with a compatible local engine/model already installed.
- Record application version, OS, RAM/GPU, exact model/quantization, engine version and whether the model was already loaded.
- Capture the screen or take timestamped notes. Record actual results, not what the developer intended.
- For the current prototype, follow `README.md` to start Rom. Record any failure caused by the developer-specific paths or profile assumptions; the future product must not depend on them.
- Ask a first-time tester to narrate what they think is happening. Let them try without coaching; record every point where help becomes necessary.

## My first session

| ID | What I do or say | What must happen | Evidence to retain |
| --- | --- | --- | --- |
| U01 | Open TZ for the first time | Product purpose, workspace and next step are understandable; no account/key/payment demand | Startup screenshot; time to first task |
| U02 | Start with no engine or model installed | Explain missing component, download size and setup steps; no silent installation | Setup messages and cancellation result |
| U03 | Look at the model/status view | Distinguish TZ, engine and model; explain whether execution is on my computer | Screenshot and tester's explanation |
| U04 | “Explain what this tool can do in three bullets.” | Useful concise answer; no unnecessary council or file changes | Answer, route and elapsed time |
| U05 | “Save a file named welcome.txt containing Hello from TZ.” | File exists inside the chosen workspace with exact content; clickable result and action receipt | File and run receipt |
| U06 | “Show me an example welcome message, but do not save anything.” | Answer only; no filesystem mutation | Before/after workspace listing |
| U07 | “Save a simple HTML page named welcome.html with the heading My first TZ page.” | Page is saved; opening follows the explicit user choice; displayed content matches | Saved file and rendered page |
| U08 | Ask a coding task that takes time | Current model/phase, elapsed time and actual progress stay visible; no invented work claims | Activity recording |
| U09 | Stop the long task | UI acknowledges stop promptly; backend cancellation is attempted and tracked; no later unannounced writes | Cancel event, backend outcome and file check |
| U10 | Ask “What did you do on my last task?” | List actual files, checks, failures and unfinished work with links | Run details matched against files |
| U11 | Close and reopen TZ | Previous run outcome can be inspected; interrupted work is labelled accurately | Recovered run record |
| U12 | Disconnect internet after model setup and repeat U04/U05 | Core local work still succeeds; no login or cloud fallback | Answers, artifacts and network observation |

U08 is the direct test of the complaint: after three minutes I must be able to tell whether the model is loading, generating, using tools, checking results, stalled or cancelled. A moving spinner alone fails.

## When something goes wrong

| ID | Scenario | Expected behavior |
| --- | --- | --- |
| E01 | Engine unavailable | Clear recovery instructions; no endless thinking indicator |
| E02 | Model unavailable | Identify exact missing model; offer eligible alternatives without silently changing task capability |
| E03 | Insufficient memory or slow large model | Explain measured problem; let me choose an eligible smaller model or stop |
| E04 | Worker returns no usable answer | Mark incomplete/failed; do not substitute internal thinking for completed work |
| E05 | Request path outside workspace, including `..` and junction escape | Reject out-of-workspace writes and show the reason |
| E06 | Destination unwritable, disk full or existing target conflict | No false “saved”; preserve original content and report partial outcomes |
| E07 | Request a cloud model or any listed OpenRouter NVIDIA identifier | Explain incompatibility with no-key/no-paid policy; no key prompt, credit flow or fallback |
| E08 | Model emits malformed or unauthorized file action | Reject action; preserve readable answer and report rejection |
| E09 | App closes during a write or stream | Recover a truthful interrupted status; avoid corrupting the original file |
| E10 | Retry a failed task | New attempt is linked to original; no duplicate unannounced side effects |

Engine adapter, network-policy and filesystem tests supplement this user session. A novice tester is not expected to prove all security properties by looking at the screen.

## Speed and clarity scorecard

These are initial goals to validate on a declared reference computer, not universal speed promises:

- Show a run ID and accepted/queued state within one second.
- While active, update elapsed time at least once per second and show meaningful phase changes as they occur. If there is no new event for ten seconds, say so without inventing progress.
- Acknowledge Stop within two seconds; separately show whether backend termination is confirmed.
- Target first visible answer text within ten seconds for a small, warm local model on a simple prompt. Record cold loads separately.
- Every terminal state has a receipt: completed, failed, cancelled or interrupted. Never label “completed” solely because the HTTP request ended.
- No API key, paid model, payment step or external inference is required in any tested path.

## Recording a result

Copy this block for each case:

```text
Test ID / date / build:
Tester and starting environment:
Exact prompt and model:
Cold or warm model:
Expected outcome:
Actual outcome:
Time accepted / first answer / finished:
Files changed and checks performed:
Evidence paths or run ID:
Pass / Fail / Not implemented / Blocked:
Severity and next fix:
```

Release gate: all no-key/no-payment and file-integrity cases pass; the complete basic session works without coaching; every long or interrupted task leaves inspectable evidence. Treat lost/corrupt files, hidden cloud execution and false completion as release blockers. Track usability failures separately from raw model speed.
