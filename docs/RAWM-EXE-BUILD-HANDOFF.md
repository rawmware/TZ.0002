# RAWM: one-time EXE setup, then launch by personal code

Date: 2026-09-13. Status: design and reference code only; nothing implemented.

## User intent and working preferences

Roman already loves the simplicity and appearance of typing `roman` in PowerShell and chatting with RAWM. Preserve that experience. New users should download and run an EXE once, enter their own passcode, then launch the AI in future by typing that code directly into PowerShell or Command Prompt. They should not need to find the EXE again or enter a second prompt every launch.

Roman explicitly requested planning only in this conversation. Code below is context for the next conversation, not executed code. When Roman asks that conversation to begin building from this document, implement this scope. This document supersedes conflicting launch/distribution ideas and the old numeric approval gate in `RAWM-CONCEPT-AND-SOL-HANDOFF.md`.

Roman reports using GPT-6 Astra High, being close to usage limits despite a recent reset, and needing careful spending. Be concise, reuse existing work, inspect only what is needed, avoid repeated research and confirmations, and use no subagents unless requested. Finish authorized work, but do not expand scope. His main concern is breaking his working setup.

## Required experience

1. Download and run `RAWM-Setup.exe` once.
2. Show: **Hello, please enter your passcode to access the AI.**
3. Configure the user's personal launch code; finish installing the complete local app.
4. Tell them: **Open a new PowerShell or Command Prompt window and type your code.** New windows are required to receive the updated PATH.
5. Typing their code, for example `myrawm7`, starts RAWM inside that same terminal. Preserve the existing chat layout, colors, streaming, model behavior, commands, and copy/paste. Exit returns to the calling shell.

Terminology: RAWM is a **local AI terminal application / CLI**. `roman` is a **launch command**. PowerShell is a shell; Windows Terminal is a terminal host.

**Passcode meaning for v1:** a user-chosen personal launch command. A bare code entered at a shell is discoverable through history and its executable filename; it is not secure password authentication. Do not promise otherwise or invent an account/licensing service. Issued customer credentials, expiry, or remote revocation require a separate design if requested. Keep the requested launch flow.

## Existing implementation, inspected read-only

- Working root: `C:\Users\ROMAN\Documents\ChatGPT\Rawm's local LLM`.
- Current inspected command: `%LOCALAPPDATA%\Microsoft\WindowsApps\roman.cmd` → `%LOCALAPPDATA%\RAWM\Launch-RAWM.ps1` → working root's `Start-RAWM.ps1` → `app\RAWM.psm1` / `Start-RAWMChat`.
- PowerShell 7 hosts the chat; local `llama.cpp` runs Qwen GGUF models. Settings currently reference 0.8B Fast and 4B Code models and loopback port `18080`.
- Settings: `config\settings.json`. Behavior: `context\RAWM-BEHAVIOR.md`. Chats/logs: `data\`.
- Registration scripts can modify profiles and the existing `roman` launcher. **Do not run those scripts for the new package.**

## Build approach and protection of the original

1. Record baseline file hashes and launch configuration; create and verify a backup before implementation. Develop a separate copy under `distribution-dev/`. Do not edit the working application's scripts, settings, models, profiles, PATH entry, or launchers. Never point the new launcher at the working root.
2. Reuse copied PowerShell chat code and the validated model/runtime combination. Use C#/.NET for a small Windows setup EXE and console launcher; verify a supported SDK and redistribution licenses at build time. Avoid a web UI, cloud API, or interface rewrite.
3. Install per user into `%LOCALAPPDATA%\RAWM-Client`, distinct from existing `%LOCALAPPDATA%\RAWM`. Bundle a private PowerShell 7 runtime, llama.cpp dependencies, and required models. A downloadable setup EXE may be large: model files are required, not magically contained in a tiny launcher. No dependency on Roman's Codex runtime or username.
4. Put the console launcher in `bin\<code>.exe`. Add only this dedicated `bin` directory to the **user PATH**, idempotently, preserving existing entries. Do not edit PowerShell profiles or require administrator access by default. Reject invalid names, Windows reserved names, `roman`, and existing shell-command collisions. Use a conservative code format such as `[a-z][a-z0-9-]{5,31}`.
5. Keep settings, new chats, and logs in the client's own folder. Ship no Roman chat history, logs, exports, credentials, or personal project context. Review packaged behavior instructions for personal details.
6. Give the copied backend a separate loopback port. If occupied, fail clearly or safely allocate another; never attach to an unrelated server. Prevent overlapping client instances in v1 and stop only processes the client owns. Match health checks to the server actually launched.
7. Provide uninstall that removes only this client's files and exact PATH entry; preserve user conversations by default. Removing the client must leave `roman` usable.

Suggested installed layout:

```text
%LOCALAPPDATA%\RAWM-Client\
  bin\<code>.exe
  Start-RAWM.ps1
  app\RAWM.psm1
  runtime\powershell\pwsh.exe  (+ required runtime files)
  runtime\llama.cpp\          (runtime and dependencies)
  models\                    (validated GGUF files)
  config\settings.json
  context\RAWM-BEHAVIOR.md
  data\                      (fresh, per-user conversations/logs)
```

## Reference launcher code — uncompiled, not production-complete

Suggested C# console entry point. Build self-contained for the target Windows architecture; consider single-file publishing for the launcher. Renaming the published launcher to the chosen code supplies the command. It starts the copied chat with inherited terminal input/output and waits for it to finish.

```csharp
using System;
using System.Diagnostics;
using System.IO;

var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, ".."));
var shell = Path.Combine(root, "runtime", "powershell", "pwsh.exe");
var entry = Path.Combine(root, "Start-RAWM.ps1");

if (!File.Exists(shell) || !File.Exists(entry))
{
    Console.Error.WriteLine("RAWM installation is incomplete. Run setup again.");
    return 2;
}

try
{
    var start = new ProcessStartInfo(shell)
    {
        UseShellExecute = false,
        WorkingDirectory = root
    };
    // ArgumentList avoids assembling a shell command from strings.
    foreach (var arg in new[] {
        "-NoLogo", "-NoProfile", "-File", entry
    }) start.ArgumentList.Add(arg);

    using var chat = Process.Start(start);
    if (chat is null) return 3;
    chat.WaitForExit();
    return chat.ExitCode;
}
catch (Exception error)
{
    Console.Error.WriteLine($"RAWM could not start: {error.Message}");
    return 3;
}
```

This sketch intentionally omits installer UI, code-name validation, PATH registration, packaging, single-instance control, cancellation/process cleanup, and backend isolation. Implement those before claiming completion. Test script execution on clean Windows; sign packaged scripts as appropriate and respect organization policy. Do not change machine-wide execution policy. Preserve terminal interaction rather than redirecting chat into a hidden process.

## Definition of done

- Clean compatible Windows machine: run setup once; both a new PowerShell and Command Prompt accept the chosen code and open the familiar chat in place.
- Local responses work offline after installation. Verify appearance, streaming, multiline paste, model switching, cancellation, exit/relaunch, and saved conversations.
- Exercise invalid/colliding codes, paths containing spaces, occupied ports, missing files, repeated setup, and uninstall. Explain hardware limits without promising identical speed on every PC.
- Verify the original application/launch files against baseline hashes and confirm `roman` still works. Do not run two model copies simultaneously on Roman's computer unless memory permits.
- Deliver the actual build, concise usage instructions, and observed verification results. No live app code was changed when this handoff was written.
