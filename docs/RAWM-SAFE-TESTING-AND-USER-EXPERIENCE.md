# RAWM: safe testing, download, and everyday experience

Date: 2026-09-13. Planning only. No installation, policy changes, shortcuts, or website publishing authorized in this conversation.

Read alongside [RAWM-EXE-BUILD-HANDOFF.md](RAWM-EXE-BUILD-HANDOFF.md). This addendum takes precedence for testing, first launch, shortcuts, and policy handling. The earlier C# sample is still illustrative. Preserve its isolation requirements and Roman's usage-budget concerns: concise work, minimal investigation, no unnecessary rewrites or repeated troubleshooting loops.

## Product intent

The terminal experience itself is the appeal: simple, effective, and satisfying to use, with the feeling of having powerful models available through a command. Preserve Roman's current RAWM appearance and interaction. A newcomer should not need to understand PowerShell administration to enjoy it. Roman eventually wants a desktop shortcut himself; **do not create it during this planning task**.

## Download and first use

1. On the Rawmware website, show **Download for Windows**, a brief compatibility/download-size note, and a picture of the actual chat. No developer vocabulary in the main flow.
2. The user downloads and opens `RAWM-Setup.exe`. A web download does not automatically install or run the app.
3. Show one small window: **Welcome to RAWM. Enter your passcode to get started.** Supporting text: **You'll type this code whenever you want to open RAWM.** Button: **Get started**.
4. Complete per-user setup automatically, with understandable progress such as **Getting your AI ready…**. Handle dependencies and model files inside setup; no manual script commands. Keep the previous plan's user-chosen launch-code meaning unless Roman specifies an issued-code system.
5. Create a **RAWM** desktop shortcut and Start menu entry. Open the terminal and start the chat immediately. **Do not require the user to enter the code a second time on this first launch.**
6. Include a short, unobtrusive reminder: **Next time, open RAWM from your desktop and type your code. You can also type it in PowerShell or Command Prompt.**

## Returning to RAWM

- **Shortcut route:** clicking RAWM opens a terminal window titled RAWM, showing **Type your RAWM code and press Enter.** The user types their launch code at the shell prompt and enters the familiar chat.
- **Command route:** open PowerShell or Command Prompt, type the same code, and chat in that window. No additional passcode dialog.
- Provide a recognizable shortcut icon and window title. The running window is visible on the taskbar, but may be grouped under its terminal host; test this and do not promise a separate branded taskbar button automatically. Do not force taskbar pinning.
- Exiting chat returns to the shell; closing the window ends the app's owned backend processes. A fresh launch remains easy.

Use **RAWM**, **your code**, **chat**, and **ready** in normal instructions. Keep terms such as CLI, inference backend, PATH, execution policy, and runtime in developer documentation. The code is a launch name, discoverable in shell history and filenames, not a secret password or secure customer authentication.

## Test without disturbing Roman's Windows setup

**A separate folder alone does not isolate installer changes.** An installer can still change the user's PATH, shortcuts, profiles, and registry.

1. Start with a portable development copy: no installer registration, persistent PATH edits, profile edits, desktop shortcuts, Windows account changes, or writes to the existing RAWM installation. Use separate data and backend ports.
2. Test the command experience through a dedicated child shell started with `-NoProfile`. Give only that child process a temporary PATH containing the test launcher's folder. This needs no profile changes and disappears when the process exits. It is configuration isolation, not a security sandbox.
3. Test actual installation, shortcuts, upgrade, and uninstall inside a disposable Windows VM or Windows Sandbox. Keep the working RAWM folder outside it; transfer only test artifacts, with any host mapping read-only. Check availability first; do not enable Windows features on Roman's host as an incidental setup step. Sandbox is disposable and is unavailable on Windows Home. [Microsoft documentation](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/).
4. Test from a real browser download in that environment, not only a local build. Check clean PowerShell and Command Prompt, no preinstalled development tools, command collisions, offline chat, and first/returning launches. Use a snapshot-capable VM for reboot/persistence checks and a compatible physical test computer for realistic performance.
5. Compare baseline profile hashes, persisted execution policies, PATH, original launcher files, and settings after testing. Confirm `roman` still works. Installing into Roman's everyday account is a separate, deliberate step after isolated verification.

End-user installation may add its own user PATH entry and shortcuts, as a normal part of this requested app installation. It must preserve existing entries and profiles; uninstall removes only what this installation owns.

## Avoid the execution-policy troubleshooting loop

`-NoProfile` skips startup profiles; it does **not** make scripts exempt from execution policy. Wrapping a `.ps1` in an EXE also does not remove that dependency.

**Recommended first implementation:** retain the copied PowerShell chat, and launch only its private child process with an explicit process-scoped policy. Do not run `Set-ExecutionPolicy` for CurrentUser or LocalMachine, modify organization policy, or ask users to paste RemoteSigned commands. Microsoft documents process policy as temporary, subordinate to Group Policy, and Bypass as intended for scripts inside larger applications. [Execution-policy documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies).

Reference replacement for the earlier C# argument list, not executed here:

```csharp
// Only the packaged chat child process; no persisted policy changes.
foreach (var arg in new[] {
    "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", entry
}) start.ArgumentList.Add(arg);
```

Use a verified package and fixed internal script paths. Keep this temporary policy out of the ordinary interactive shell opened by the desktop shortcut. Organization restrictions still apply; provide a clear explanation if blocked, not a workaround that defeats them. Test cancellation and cleanup explicitly.

If the requirement becomes **no PowerShell script-policy dependency at all**, use a compiled C# console chat client while preserving the interface and local model engine. That is additional implementation work, not something a launcher wrapper achieves; do not start that rewrite by default.

## Release through Rawmware

Prepare a versioned installer and complete model/runtime payload, sign the installer and application, and host downloads over HTTPS. The website button can link to separate release/file hosting; inspect the actual website and file-size limits when publishing is authorized. Verify model/runtime redistribution terms, release integrity, and the complete browser-to-chat journey before making the link public. No personal chats or credentials in the package.

Signing establishes publisher identity but does not guarantee a new download avoids SmartScreen warnings. Treat this as a release-quality issue distinct from PowerShell policy; never instruct users to disable Windows protection. [Microsoft guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

Success means: **download → enter code once → chat opens; later, desktop shortcut → type code → chat**, with the direct shell-command route also working, and no changes to existing PowerShell profiles or persisted execution policies.
