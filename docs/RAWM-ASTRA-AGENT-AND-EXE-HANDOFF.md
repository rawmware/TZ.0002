# Astra handoff: RAWM local agent and future EXE integration

Date: 2026-09-14

## Current status and Roman's direction

Roman asked Astra to turn the local-agent vision into working application code, then clarified that RAWM must be a capable assistant for files and other tasks, with Notepad serving only as an initial desktop example.

The agent foundation is implemented in the existing source application. **No EXE or installer was built, installed, or published.** Roman will test the application himself. Do not run more model, launcher, desktop, or application tests unless Roman explicitly requests them. Keep future work focused and conserve tokens.

An already-open RAWM process holds the old module in memory. After source changes, enter `/exit`, then run `roman` again to load them.

## What Astra changed

| File | Change |
| --- | --- |
| `app/RAWM.psm1` | Integrated agent commands and natural-language file inspection into the existing chat. Preserved normal chat and model routing. Added loopback-only HTTP handling and session-owned backend startup. |
| `app/RAWMAgent.ps1` | Added the tool registry, direct request parsing, local-model JSON planning, deterministic policy checks, exact plan previews, approvals, cancellation, execution, verification, and local audit logging. |
| `app/RAWMFiles.ps1` | Added read-only analysis of explicitly selected local text/code files, including files outside the write workspace. |
| `app/WindowsNotepad.ps1` | Implemented a Windows UI Automation adapter for a new Notepad draft, verified target/focus, literal insertion, and text read-back. Live desktop behavior remains unverified. |
| `config/settings.json` | Enabled the agent and selected the existing `code` model slot for planning and file review. Added the enabled-tool list. |
| `context/RAWM-BEHAVIOR.md` | Clarified that chat prose cannot execute tools or claim actions occurred. |
| `README.md` and agent documentation | Added capability examples, usage instructions, architecture, and limitations. |
| `tests/Test-RAWMAgent.ps1`, `tests/Test-RAWMLaunchers.ps1`, `tests/Test-RAWMLive.ps1` | Added repeatable checks and isolated fixtures. Leave further execution to Roman unless requested. |
| `.gitignore` | Excluded private chats, logs, exports, workspace contents, large local dependencies, and test fixtures. |

The existing `roman` registration already points to this source folder. The registration scripts, shell profiles, PATH, persisted execution policy, installed models, and existing launcher files were not modified during this work.

## What RAWM can now do

### Review a selected file with its local model

```text
Check "C:\path\script.py" for bugs
Explain "C:\path\settings.json"
Summarize "C:\path\notes.md"
/inspect "C:\path\script.py" Why is this returning the wrong result?
```

Use a real quoted path. Inspection reads one text/code file and asks the configured local model to analyze it. It can explain content and suggest fixes with line references. It does not execute or edit that file. Selecting a file does not authorize writes to its directory.

The source is supplied to inference temporarily. Saved chat contains the user's question and the resulting review, which may quote excerpts; the complete source prompt is not attached to chat history. Size, context, path, and credential-like-content checks apply. PDF, Office, and image reading are not implemented.

### Work with files inside RAWM's workspace

```text
List workspace files
Create file "notes.txt" containing "Hello Roman"
Read workspace file "notes.txt"
Rename "notes.txt" to "ideas.txt"
/act Create a file named first.txt containing exactly alpha, then rename first.txt to second.txt.
```

The write workspace is `<RAWM folder>\workspace`. File tools support `.txt`, `.md`, `.csv`, `.json`, and `.log`. Creates cannot overwrite existing files. Renames require approval. The model can propose up to four steps, and all model-generated plans require approval of the displayed plan ID.

### Use the controller

```text
/agent
/agent on
/agent off
/act <request>
/approve <displayed-id>
/cancel
/agent audit
```

Approvals expire after five minutes and are single use. Unsupported tools cannot be enabled by model output. Execution stops at the first failure and records completed steps. The audit log is `data/agent/audit.jsonl`; it records paths and outcomes but excludes typed/file text.

`Show system info` is also supported. `Open Notepad and type "hi"` uses the implemented desktop adapter, whose live test is still pending.

## The startup regression and correction

Astra initially added a check that refused startup when local port `18080` was occupied. Roman reported that this prevented even `hello?` from working. The earlier isolated checks had not caught this everyday startup condition.

The correction in `Start-RAWMServer` now:

1. Tries the configured local port.
2. If it is unavailable, asks Windows for a free local port.
3. Uses that port for health checks, chat, planning, and file inspection in the current session.
4. Leaves the saved configuration unchanged.
5. Gives each backend process/port its own log filenames.
6. Stops only the backend process owned by the current RAWM session.

The current application must be exited and reopened to load this correction. **Astra did not run application tests after Roman asked to take over testing.** A short port-reservation-to-process-start race still exists; packaging should handle a rare bind failure with a bounded retry when that work is authorized.

## What was verified before Roman took over testing

- 86 policy/filesystem/inspection checks passed.
- The existing `roman` command launched through PowerShell 7, Windows PowerShell, and Command Prompt in child-process checks.
- The Windows UI Automation adapter compiled without opening an application.
- The local 4B model produced a file-creation plan, waited for approval, then created the expected contents.
- Local file review identified an intentional subtraction-versus-addition bug on line 2; the source file was unchanged.
- The local model produced a create-then-rename plan; approval and both file verifications completed.
- An unsupported deletion request was rejected without execution.
- A fresh ordinary chat returned `ready` in the final local-model check.

These are earlier development checks, not a claim that the full product is release-ready. The final port-fallback correction has not been runtime-tested by Astra. The live Notepad test was declined at the desktop permission prompt and did not run. Windows Terminal visual behavior and clean-machine installation remain unverified.

## How to include this in the future EXE app

This extends the existing terminal-based EXE plan. Read alongside [the EXE build handoff](RAWM-EXE-BUILD-HANDOFF.md) and [the safe testing and everyday experience guide](RAWM-SAFE-TESTING-AND-USER-EXPERIENCE.md). Their historical statements that agent implementation had not started no longer describe the source code listed here. Their isolated-distribution approach still applies when Roman authorizes EXE work.

### 1. Freeze the version Roman has accepted

After Roman finishes trying the app, record the accepted source version and make a backup. Start EXE development from a separate `distribution-dev` copy. The new package must never point its launcher at Roman's working source directory.

### 2. Package all agent modules

The EXE launcher should start the packaged PowerShell 7 runtime and the copied `Start-RAWM.ps1`. That script loads `app/RAWM.psm1`, which loads the agent modules. Include all three supporting `.ps1` files; copying only the original `RAWM.psm1` will leave the agent incomplete.

Suggested installed layout:

```text
%LOCALAPPDATA%\RAWM-Client\
  bin\<chosen-code>.exe
  Start-RAWM.ps1
  app\
    RAWM.psm1
    RAWMAgent.ps1
    RAWMFiles.ps1
    WindowsNotepad.ps1
  runtime\powershell\pwsh.exe   (+ its dependencies)
  runtime\llama.cpp\            (validated native runtime)
  models\                       (validated GGUF models)
  config\settings.json
  context\RAWM-BEHAVIOR.md
  workspace\                    (initially empty)
  data\chats\                   (initially empty)
  data\logs\                    (initially empty)
  data\agent\                   (initially empty)
```

The EXE is a launcher/setup layer around RAWM. It does not replace the model files, native inference engine, controller, or PowerShell modules. Reuse the current native controller; Qwen Code and Node.js are not required dependencies for this implementation.

### 3. Remove development-machine assumptions

- Bundle a supported private PowerShell 7 runtime; do not depend on Roman's Codex cache.
- Use package-relative model paths and a validated llama.cpp build.
- Ship fresh settings and an empty workspace/data tree.
- Exclude Roman's chats, logs, exports, test fixtures, selected-file paths, and personal context. Git ignore rules alone are not a packaging filter; use an explicit package file list.
- Review the behavior prompt so a distributable app does not address every customer as Roman.
- Validate the Notepad adapter's Windows PowerShell/UI Automation dependency on supported target machines. Keep chat and file features usable if the adapter is unavailable.

### 4. Build the setup and launch experience

Follow the existing agreed flow: `RAWM-Setup.exe` asks for a personal launch code, installs the private application, creates the requested shortcuts, and opens chat on the first launch. Later, a shortcut or the chosen command opens the same terminal experience. The launch code is a command name, not secure authentication.

Keep `%LOCALAPPDATA%\RAWM-Client` separate from the existing `%LOCALAPPDATA%\RAWM`. Preserve the working `roman` command. Avoid command-name collisions. Do not rerun the current registration scripts as part of distribution development. Any launcher policy setting must be confined to its private child process and respect organization policy; do not alter persisted Windows security settings.

### 5. Carry the agent controls into the package

Keep the agent status visible, retain `/agent off`, show concrete plans before approval, and preserve local-only inference. Preserve file-read/write boundaries, audit behavior, cancellation, and verification. Use independent data folders and backend ports. Upgrade/uninstall behavior must preserve user chats and workspace files by default.

### 6. Let Roman decide when release validation happens

When Roman authorizes packaging validation, use a disposable Windows environment to check installation, direct command launch, shortcuts, offline chat, model routing, file review, file workflows, desktop compatibility, occupied-port recovery, cancellation, upgrades, and uninstall. The current working installation must stay separate.

Do not build, install, publish, change profiles/PATH, or run additional application tests merely because this document describes those future steps. Roman will authorize EXE work when ready.

## Remaining scope

This is an extensible first agent foundation. It is not yet a general desktop operator. Arbitrary shell commands, broad file editing, browser automation, document/image readers, speech input, background tasks, and advanced project-wide workflows are not implemented. Credential detection is a heuristic and filesystem checks are not an OS sandbox against concurrent changes by other software.

Useful future additions are bounded project search, approved exact file edits with backups, and additional application adapters. Add these through the same controller with narrow arguments and observable results. Notepad must remain one example tool, not the definition of RAWM's agent capability.

## Ready-to-use continuation request

> Use RAWM-ASTRA-AGENT-AND-EXE-HANDOFF.md and the existing EXE experience documents to package the version of RAWM I have accepted. Preserve my working roman application. Include the native agent and file-review modules in a separate distribution copy. Do not run application tests unless I specifically ask; tell me what I should try myself.
