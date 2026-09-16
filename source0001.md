# Desktop bridge: tz-desktop-bridge-v1

## Source and installation

Built from private `rawmware/TZ.01` main commit `846ab1c3f659989424d63afff939a25038ed9392`, fetched read-only. Destination `rawmware/TZ.0002` began at `f030a23225816584061bcb9bda992acef860043a`. The new source was assembled on `codex/desktop-bridge` in `C:\Users\rjcot\TZ.0002`, outside the existing OneDrive directory. No push or source change was made to TZ.01. Release tag `tz-desktop-bridge-v1` identifies the delivery commit; use `git rev-parse tz-desktop-bridge-v1` to obtain its hash.

The actual laptop was not connected. Its published source and handoffs were the comparison evidence. Desktop TIZI contained only README.md, rom.instructions.md and rom.ps1, in an unborn Git repository with no remote. Laptop source already contained the modular agent, persistent conversations, deterministic tools, file inspection, browser/Notepad adapters, cancellation and worker routing. Those modules are now included intact except for the focused backend adaptations below. Older documents record historical work and future proposals, not additional installation commands to execute automatically.

## Root cause and repair

The old rom.ps1 was UTF-8 without a BOM. PowerShell 7 parsed it successfully. Windows PowerShell 5.1 decoded the same bytes using its legacy default encoding and reported the documented errors at lines 358, 531, 555 and 571, among others. Adding a UTF-8 BOM eliminated all parser errors under 5.1, without changing executable text. The problem was encoding, not stray action markup or an unterminated here-string.

Original bytes remain in `C:\Users\rjcot\OneDrive\Documents\ChatGPT\TIZI\rom.ps1.backup-20260915234339`. That directory was not replaced. The new project's rom.ps1 is a compatibility wrapper for the modular Start-RAWM.ps1 entry point.

The desktop helper `C:\Users\rjcot\ollama_commands.ps1` already dot-sourced the old script. Its import now points to `C:\Users\rjcot\TZ.0002\rom.ps1`, so its preexisting Rom function is overridden by the recovered app wrapper. Original helper: `C:\Users\rjcot\ollama_commands.ps1.backup-20260915234339`. PowerShell profile files themselves were not edited.

## Dependencies and backend

No runtime, package or model downloads were needed. Used existing PowerShell 7 at `C:\Users\rjcot\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe` and the existing Ollama service on loopback port 11434. Windows PowerShell 5.1 is used only for compatibility/bootstrap and the existing Notepad adapter.

`Install-Desktop.ps1` generated ignored `config/settings.local.json` from the checked-in laptop configuration, selecting backend `ollama`, fast model `gemma3:1b`, coding model `qwen3.6:latest`. Installed `gemma4:26b` remains available to the existing worker configuration. The complete local settings file takes precedence over settings.json. The checked-in default retains llama.cpp for the laptop configuration. Custom Ollama host/port and model names belong in the local file; inference host validation remains loopback-only.

The adapter uses Ollama's OpenAI-compatible streaming endpoint, validates installed model names, reports actual model/runtime in `/model` and `/usage`, and leaves the shared Ollama server running on exit. File inspection uses a conservative UTF-8 byte upper bound because Ollama has no llama.cpp `/tokenize` endpoint. Large excerpts fail visibly. Ollama owns model storage; no weights were copied. No user OLLAMA_MODELS override was present. Configure OLLAMA_MODELS in Ollama's environment and restart Ollama if relocating its storage. Laptop GGUF paths remain relative to the app, or can be absolute in local settings.

## Windows registration

Executed `./Install-Desktop.ps1` in PowerShell 7 from the new install directory. It created `%LOCALAPPDATA%\TZ\bin\roman.cmd` and `rom.cmd`, prepended that dedicated directory to user PATH, and set user `TZ_HOME` to the new install directory. Prior PATH and TZ_HOME values are saved in `%LOCALAPPDATA%\TZ\registration.json`. The shims launch the discovered PowerShell 7 executable with NoProfile and Start-RAWM.ps1; no ISE or session alias is required. ExecutionPolicy Bypass applies only to the child process; no persisted execution-policy setting changed.

Created `Roman TZ.lnk` on the Desktop and in the user's Start-menu Programs directory. Broadcast the Windows environment-change notification. Existing terminal processes retain their old environment: reopen the terminal, or use the shortcut immediately. If an already-running terminal host still inherits stale PATH, restart that host or sign out/in.

Final command in Command Prompt or PowerShell: `roman` (alias command `rom`). The application remains a terminal agent with native launch shortcuts; this is not a packaged GUI/EXE installer.

## Reproduction on another desktop

1. Clone TZ.0002 into a separate folder. Preserve any existing install.
2. Ensure PowerShell 7, Ollama and desired local models already exist (`ollama list`).
3. In PowerShell 7 run `./Install-Desktop.ps1 -FastModel 'gemma3:1b' -CodeModel 'qwen3.6:latest'`, substituting installed names as needed. The installer checks availability and does not download models.
4. If an old profile defines Rom/Roman, back up and redirect its helper import to this project's rom.ps1. This desktop-specific helper edit was performed separately; the installer does not rewrite profiles.
5. Open Roman TZ or run `roman` in a fresh terminal. Use `/model`, `/workers`, `/help`, `/fast` and `/code` as needed.

## Verification and limits

- Old rom.ps1: zero parser errors in Windows PowerShell 5.1 after BOM repair.
- Test-DesktopBridge.ps1: actual launches through cmd.exe, Windows PowerShell 5.1 and PowerShell 7; action cancellation, runtime/model display and clean exit; actual Ollama streaming returned Ready; missing-model error and preservation of shared service verified. Coding-model name/availability checked without running a large coding generation.
- Existing suites: 87 agent-policy checks, 88 conversation checks and 61 reliability checks passed.
- Existing worker suite stopped at its unconditional Codex CLI lookup: that optional CLI is absent on this desktop. Qwen CLI is present. No external worker execution was claimed or tested.
- Desktop Notepad typing, browser page loading, physical cancellation keys and large coding generations were not exercised. These retain the laptop implementation and its stated limitations. No general desktop operator, voice feature or packaged EXE was added.
- Launcher currently records the existing Codex-cached PowerShell executable. If that runtime moves, run the installer again from an installed PowerShell 7. A self-contained redistribution still needs a bundled runtime and separate release validation.
- Git excludes chats, workspace files, logs, test runs, local settings, runtime directories, caches, credentials and all model weights. Only explicit source/documentation paths were staged; model directory contains only .gitkeep.

## Rollback

Run `./Uninstall-Desktop.ps1` to remove the dedicated PATH entry, both shims and shortcuts, restoring prior TZ_HOME when it still identifies this installation. Chats, source, model storage and backup records remain. Restore the backed-up ollama_commands.ps1 if returning to the old profile setup. Keep the BOM-fixed old rom.ps1 for working 5.1 parsing; restore its byte-for-byte backup only if intentionally returning to the original broken encoding. Restart the terminal host or sign out/in. GitHub rollback, if needed, should be a normal revert in TZ.0002; never reset or overwrite TZ.01.
