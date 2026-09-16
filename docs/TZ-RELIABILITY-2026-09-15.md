# TZ reliability changes — September 15, 2026

TZ is the product discussed in Roman's test session. The existing RAWM file layout and `roman` launch command remain the implementation. The attached session supplied examples and observed failures; its embedded commands were not executed as user instructions.

## Implemented behavior

- **Direct browser actions:** phrases from the session, including greetings, Chrome-or-Edge selection, “open up YouTube,” and YouTube cooking-video searches, produce a native `browser.open` plan. No model or external agent is needed. Explicit Chrome/Edge selection is respected; otherwise Edge is tried before Chrome. The plan shows the full address. Windows receives a separate executable argument, not shell command text. Only HTTP(S) URLs and the fixed blank-page destination are accepted. This launches a visible browser; it does not operate page contents.
- **Bounded execution:** a shared wait helper polls for cancellation and enforces deadlines across process execution, HTTP response headers, stream reads, and output collection after a process exits. Notepad uses one structured result line and isolates the editor's standard streams from the helper. It no longer depends on a long-lived editor closing its inherited output pipe.
- **Cancellation:** active operations capture Escape and Ctrl+C in the TZ terminal and restore the previous console mode afterward. Workers close stdin, start in the workspace, and terminate their process tree when interrupted. Notepad cancellation leaves the draft available for inspection. Already completed changes are not rolled back.
- **Clear progress:** waiting operations show the current task and elapsed seconds every five seconds. Generation does not display hidden reasoning or fictional activity. Streaming responses continue to show their real usage summary.
- **Application state:** “is the agent active right now?” reads the live setting directly. “Show workers” and “copy the last answer” also bypass inference. Copy confirmation does not replace the last answer.
- **Code drafts:** requests to generate code in Notepad use the installed local coding model directly. The full generated text appears before approval. Long drafts display as readable multiline text rather than an escaped JSON string inside a narrow box. Notepad supports 16,000 characters; ordinary workspace file creation retains its 4,000-character cap. Truncated, empty, oversized, or structurally incomplete HTML responses are rejected. Code is not executed by this path.
- **Honest worker results:** the preview includes the exact task. Successful worker exit is recorded as a report, not verified completion. Browser launch is recorded as launched, not page-load verification. Automatic worker selection excludes Codex; explicitly selected Codex is identified as a separately authenticated service.

## Verification

Automated regression suites cover policy, conversation, worker routing, interface identity, and reliability. The new tests exercise the session's browser phrases; references versus instructions; unsafe URI rejection; approval, cancellation and replay; actual status; literal versus generated text; draft truncation; pending asynchronous reads; process deadlines; stdin closure; workspace selection; and cancellation of a real test worker plus its child process.

The existing `roman` command passed launcher checks in Command Prompt, Windows PowerShell, and PowerShell 7. The Windows UI Automation Notepad helper compiled without opening an application.

### Real model observations

The first code-draft run completed generation but exceeded the old 4,000-character cap. The draft limit was corrected. A second run produced a full HTML document and reached approval after roughly two minutes; declining created no Notepad draft. Inspection of that generated sample found a JavaScript bug: it reassigns a `const` array. Structural generation success is **not** a claim that the generated program works. This remains a model-quality limitation and the draft is explicitly reviewable, unexecuted output.

The initial streaming chat format test returned `yes` when asked for `ready`. After adding a direct instruction to preserve the requested wording and format, the isolated live streaming check returned `ready`. This one successful test does not establish general model accuracy.

Live desktop verification was declined at the execution permission prompt. The actual new Notepad entry path, browser window/page loading, and physical keyboard cancellation behavior therefore remain unverified in this session. No attempt was made to bypass that decision.

## Running checks

From the project directory in PowerShell 7:

```powershell
./tests/Test-RAWMAgent.ps1
./tests/Test-RAWMConversation.ps1
./tests/Test-RAWMWorkers.ps1
./tests/Test-RAWMInterface.ps1
./tests/Test-RAWMReliability.ps1
./tests/Test-RAWMLaunchers.ps1
```

Optional model check (may take two minutes; exact wording is a model-quality check):

```powershell
./tests/Test-RAWMCodeDraftLive.ps1
```

Explicit desktop tests, which open visible applications and leave them open:

```powershell
./tests/Test-RAWMNotepadEntry.ps1 -Approve
./tests/Test-RAWMBrowserLive.ps1
```

Fixtures and generated samples remain under ignored `tests/.runs`. No models or agent packages were installed, and no user shell/profile settings were changed.

## Remaining limits

The local coding model is still slow and can generate incorrect programs. Broad delegated tasks still depend on their external worker and are not independently verified. Browser actions launch pages and searches; they do not click, watch, or inspect videos. Mouse selection and Ctrl+C copying depend on the host terminal; the natural-language copy action offers another route. The terminal needs focus for its cancellation keys. Native desktop compatibility still needs the declined live check.

Implementation references: Microsoft's documentation for [redirected process output](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.processstartinfo.redirectstandardoutput) and [console key handling](https://learn.microsoft.com/en-us/dotnet/api/system.console.readkey).
