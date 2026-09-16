# Get the current TZ source on another computer

The repository contains the application source and documentation. It deliberately does not contain model weights, installed runtimes, account credentials, or personal chat data. Uploading the code does not itself synchronize either running installation.

## First download: keep the current installation intact

Sign in to GitHub with an account that can access the private repository. Clone into a **new folder**, outside the existing TZ/RAWM installation:

```powershell
git clone --branch main https://github.com/rawmware/TZ.01.git TZ.01-from-GitHub
```

Alternatively, use **Code → Download ZIP** in GitHub and extract into a new folder.

This gives you a separate copy to inspect. It does not replace files in an existing installation or register a new `roman` command. Do not extract over the current application directory or run a hard reset/clean against it.

## Later source updates

Inside the separate clone:

```powershell
git status
git pull --ff-only
```

If local changes conflict, stop and preserve them before deciding how to combine versions. Do not force-push, force-checkout, reset, or delete the old installation to resolve a mismatch.

## Before running the downloaded copy

- Read the root README and the current configuration.
- Confirm PowerShell 7 and a compatible local inference runtime are available on that computer.
- The supplied configuration expects the named local GGUF files. Those files are intentionally absent from GitHub.
- Existing models can be reused deliberately, or the included installer can obtain dependencies when requested. No installer or registration script was run for this upload.
- Keep the existing machine's profiles, launchers, settings, models, runtime, and personal data until the separate copy has been checked.

Do not assume that a source-only clone is a ready-to-run bundled installer. Integrating it with the existing desktop installation is a separate step, after reviewing that installation's paths and dependencies.

## What this upload changed

Only GitHub received the source snapshot, plus the new `markdown/` documentation folder. Locally, only that documentation folder was added. The existing application code, installed dependencies, source Git configuration, profiles, and launcher registration were left unchanged.
