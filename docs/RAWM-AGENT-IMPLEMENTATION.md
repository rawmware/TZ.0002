# Local agent implementation

Updated behavior and verification: [Natural-language actions](RAWM-NATURAL-LANGUAGE-FIX.md).

## Architecture and foundation

The existing startup stays `roman` -> registered launcher -> `Start-RAWM.ps1` -> `Start-RAWMChat` in `app/RAWM.psm1`. The launcher already points at this source tree. Registration, PATH, profiles, and persisted execution policies were not changed for this work.

The application owns a local llama.cpp server, streams chat completions, routes between the configured `fast` and `code` GGUF models, and saves conversation JSON under `data/chats`. The extension loads `RAWMAgent.ps1` and `RAWMFiles.ps1` inside the existing module. Model files can be relative to the package or absolute local paths. Backends are constrained to loopback; HTTP proxying and redirects are disabled. Startup prefers the configured port and selects a free local port when it is occupied. The selection stays in session memory, and server logs use process/port-specific filenames.

The foundation is a RAWM-native controller. Qwen Code is a separate terminal coding agent, and adopting it is unnecessary for the installed llama.cpp models. The current upstream package is `@qwen-code/qwen-code`; its current installation guide describes standalone releases with a private Node runtime and an npm fallback requiring Node 22+. Its README documents local Ollama/vLLM providers. Those current instructions do not establish exactly what the earlier interrupted Node 20 installer did. A `qwen` command was not found in this session, while Ollama and the bundled Codex Node runtime were present. No installation was attempted.

Sources checked:

- [Qwen Code installation guide](https://github.com/QwenLM/qwen-code/blob/main/scripts/installation/INSTALLATION_GUIDE.md)
- [Qwen Code README](https://github.com/QwenLM/qwen-code)
- [llama.cpp structured output](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Microsoft UI Automation ValuePattern](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.valuepattern.setvalue)
- [Microsoft EM_REPLACESEL](https://learn.microsoft.com/en-us/windows/win32/controls/em-replacesel)

## Controller

Whole-request parsers recognize a few exact, low-risk requests. Other actionable requests and `/act` use a local model with a bounded JSON schema. Tool names appear before arguments in the schema; this matters for grammar-constrained generation with small models. The controller validates version, field names, argument types, step count, tool permissions, path containment, file extensions, and text limits independently of the model.

Plans contain one to four tool calls. All submitted plans wait for `y` or `n`; an internal single-use ID binds approval to the displayed snapshot. The executor separately requires approval for Notepad and filesystem writes. Pending plans are serialized snapshots held only in memory, expire after five minutes, and are invalidated on cancellation or session changes. Execution revalidates permissions and paths before each step and stops on failure. An attempted tool needs a successful write-ahead audit record before it executes. No model content is evaluated as PowerShell or shell code.

Read-only inspection accepts one explicitly selected file outside the write workspace. It checks type, size, links, network paths, and credential-like content, counts tokens with the local backend, then builds an ephemeral line-numbered prompt. The inference flow has no tool execution hook. Only the resulting review and user question join the conversation, allowing follow-up discussion without granting more filesystem authority.

## Desktop adapter

`WindowsNotepad.ps1` runs in a hidden Windows PowerShell STA helper because the built-in .NET Framework UI Automation assemblies are available there. A base64-encoded JSON payload is delivered through stdin, never as executable text or command arguments. The payload is an encoding, not encryption, and is not persisted.

The adapter creates an empty GUID-named scratch `.txt` file and launches the fixed System32 Notepad executable. It identifies the matching Notepad window and a single supported native editor through UI Automation. Before inserting text it checks executable location, process ID, root window, foreground focus, editor focus, and an empty document. `EM_REPLACESEL` targets the editor handle, provides an undoable insertion, and does not use global SendKeys. Read-back must exactly match normalized text and the scratch file must still be empty before success is reported.

The main process bounds the helper lifetime, supports cancellation, and terminates only its own helper. It leaves any open Notepad draft for the user to inspect. The live desktop test has not run; adapter compatibility with this machine's Notepad is therefore still unverified.

## Verification

The current build's test results and remaining live desktop limitation are recorded in [Natural-language actions](RAWM-NATURAL-LANGUAGE-FIX.md). Earlier testing notes below describe the original foundation.

Run with PowerShell 7:

```powershell
.\tests\Test-RAWMAgent.ps1
.\tests\Test-RAWMLaunchers.ps1
.\tests\Test-RAWMLive.ps1 -Model
# Explicit live desktop test, opens and types into one new Notepad draft:
.\tests\Test-RAWMLive.ps1 -Notepad
```

Policy tests cover schema rejection, paths, links, credentials, size caps, agent-off/tool-off behavior, local-only endpoints, literal file writing, overwrite refusal, approval matching/expiry/replay, cancellation, verification, and fail-closed audit behavior. Fixtures remain under ignored `tests/.runs` for review.

Launcher checks exercise the existing `roman` command through PowerShell 7, Windows PowerShell, and Command Prompt in hidden child processes. They toggle agent mode, attempt a disabled desktop action (which must not launch anything), run system inspection, and exit. They also compile the desktop adapter without opening an app. They do not modify registrations or profiles. Windows Terminal's visual host behavior has not been tested.

Live model checks copy application/configuration/runtime files to an isolated fixture, share model files by absolute read-only use, select a separate local port, test structured planning/approval, file inspection, a multi-step workflow, rejection of an unsupported destructive request, and ordinary chat. Only the test's own server is stopped. Existing models and running user servers are not modified.

## Limits and next capabilities

This is a usable first agent foundation, not complete general computer automation. Small models can still misunderstand requests; preview and deterministic policy prevent unsupported execution but cannot prove that every allowed plan matches intent. File-review output is a model opinion, not proof that code is correct. There is no OS sandbox against concurrent filesystem replacement by another process. No background tasks, persistent permissions, arbitrary shell, network, document conversion, image understanding, speech recognition, or general browser/application automation is implemented.

Add future capabilities through the registry with narrow structured arguments, clear permissions, audit handling, cancellation, and observable verification. A useful next increment is approved exact file edits with backups and bounded project search. More applications should get dedicated adapters rather than unconstrained global keyboard input.
