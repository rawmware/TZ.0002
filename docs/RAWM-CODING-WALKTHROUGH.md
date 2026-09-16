# RAWM coding walkthrough

## The code behind the `roman` command

This is the coding notebook for Roman's local RAWM application. It focuses on the actual commands, files, syntax, and pieces of code used to make the PowerShell AI chat work.

The guide is written for someone who can describe a product clearly but is still learning programming fundamentals. You do not need to memorize everything. The goal is to let you look at the project and say, “I know what this file is for, what language is reading it, and where to look when I want to understand or change a behavior.”

This file is documentation only. It does not replace or modify the application. The E-drive version is outside the scope of this guide.

## 1. What was actually built

The working local version is a PowerShell terminal application. Its main path is:

```text
You type roman
      |
      v
PowerShell profile or roman.cmd
      |
      v
Start-RAWM.ps1
      |
      v
app/RAWM.psm1
      |
      +--> config/settings.json
      +--> context/RAWM-BEHAVIOR.md
      +--> data/chats/*.json
      +--> runtime/llama.cpp/llama-server.exe
      +--> models/*.gguf
      |
      v
Local AI response in the same PowerShell window
```

The application has several layers:

| Layer | What it does | Main file type |
|---|---|---|
| Entry command | Gives you a short command to open RAWM. | `.ps1`, `.cmd` |
| Launcher | Finds the application root and starts the chat. | `.ps1` |
| Chat application | Reads input, routes messages, calls the local AI server, and saves chats. | `.psm1` |
| Settings | Stores paths, model names, limits, and display choices. | `.json` |
| Behavior instructions | Tells the local model how RAWM should respond. | `.md` |
| Inference engine | Performs the model calculations. | `.exe`, `.dll` |
| Model weights | The learned numerical data used by the engine. | `.gguf` |
| Saved state | Stores conversations and logs. | `.json`, `.log` |

The important programming idea is **separation of responsibilities**. The launcher does not contain the entire chat app. The settings file does not run the model. The model file does not know how to display a PowerShell prompt. Each piece has a job, and the pieces communicate through paths, values, function calls, and a local HTTP request.

## 2. File type rules: where each code sample belongs

Before looking at syntax, identify the reader. A file is not “code” in the abstract. It is text or binary data interpreted by a particular program.

| If you see this | Save it as | Put it here in RAWM | Read by |
|---|---|---|---|
| PowerShell commands and functions | `.ps1` | `Start-RAWM.ps1`, `Register-RAWM.ps1`, or another script | PowerShell |
| Reusable PowerShell functions | `.psm1` | `app/RAWM.psm1` | PowerShell's module system |
| Windows command-shell instructions | `.cmd` | `roman.cmd` in the local command folder | `cmd.exe` |
| Names and values in braces with JSON punctuation | `.json` | `config/settings.json` or `RAWM.portable.json` | `ConvertFrom-Json` or another JSON reader |
| Human-readable notes with headings and code fences | `.md` | `docs/`, `README.md`, or `context/` | People or a Markdown viewer |
| A compiled Windows program | `.exe` | `runtime/llama.cpp/` | Windows |
| A compiled supporting library | `.dll` | Next to the runtime executable | The `.exe` |
| Model weights and metadata | `.gguf` | `models/` | `llama-server.exe` |

Do not save a PowerShell function in a `.json` file just because both are plain text. JSON has a data grammar; PowerShell has a programming grammar. The extension is a clue to the reader, but the contents must also match that reader's rules.

The Markdown examples in this document are intentionally placed inside fenced blocks. A fence beginning with ` ```powershell ` tells a Markdown viewer, “the following text is PowerShell code.” It does not cause the code to run.

## 3. The exact inspection commands used

The first task was to understand what was really on the computer. These commands were read-only inspections.

### Read a PowerShell profile

**Typed directly into PowerShell.**

```powershell
Get-Content -LiteralPath 'C:\Users\ROMAN\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1'
```

`Get-Content` reads a file. `-LiteralPath` tells PowerShell to treat the path exactly as written. The single quotes keep the path together as one text value.

The same command was used for the PowerShell 7 profile:

```powershell
Get-Content -LiteralPath 'C:\Users\ROMAN\Documents\PowerShell\Microsoft.PowerShell_profile.ps1'
```

### List the project files

**Typed directly into PowerShell.**

```powershell
Get-ChildItem -Force
```

`Get-ChildItem` lists files and folders. `-Force` includes hidden items. In a project, this is a quick way to learn whether you are standing in the folder you think you are in.

To search recursively for relevant file types:

```powershell
rg --files -g AGENTS.md -g '*.ps1' -g '*.psm1' -g '*.json' -g '*.md' -g '*.txt'
```

`rg --files` searches for file paths quickly. Each `-g` adds a filename pattern. The single quotes protect patterns such as `*.ps1` from being changed before `rg` receives them.

### Ask PowerShell what `roman` means

**Typed directly into PowerShell.**

```powershell
Get-Command roman -All | Format-List Name,Source,Definition
```

This is a very useful debugging command. PowerShell may find a function, script, alias, or application. `-All` shows every match. `Format-List` displays selected properties vertically.

The important question was whether `roman` resolved to the E-drive version, the C-drive version, a profile function, or a command file. That was more reliable than guessing from the command's name.

### Check execution policies

**Typed directly into PowerShell.**

```powershell
Get-ExecutionPolicy -List
```

This shows policy values by scope. A blank or `Undefined` value in one row does not necessarily mean scripts are allowed; another scope or the default can determine the effective policy.

### Inspect the app's main source

**Typed from the RAWM project folder.**

```powershell
Get-Content app\RAWM.psm1
```

This prints the reusable application module. For a smaller view, PowerShell can select a portion:

```powershell
Get-Content app\RAWM.psm1 | Select-Object -Skip 170 -First 80
```

`Select-Object -Skip 170 -First 80` means “ignore the first 170 lines, then show 80.” This is useful when the function you want is known to be lower in the file.

## 4. The actual repair commands

These commands changed the local setup during the repair. They are recorded for learning and history. Your application is already installed; do not rerun a download command just to read this guide.

### Re-register the local command

**Script file:** `Register-RAWM.ps1`  
**Command typed from the local RAWM folder:**

```powershell
.\Register-RAWM.ps1 -AllPowerShellEditions
```

The starting `.` and backslash mean “run the script in the current folder.” The switch `-AllPowerShellEditions` tells the script to update both the Windows PowerShell and PowerShell 7 user profiles.

The registration script also created the local fallback files:

```text
C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1
C:\Users\ROMAN\AppData\Local\Microsoft\WindowsApps\roman.cmd
```

### Allow local scripts for the current Windows user

**Typed through PowerShell without changing the whole computer's policy:**

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

`Set-ExecutionPolicy` changes a policy. `-Scope CurrentUser` limits the change to Roman's Windows user. `RemoteSigned` allows local scripts and places additional signature requirements on scripts marked as downloaded. `-Force` suppresses the confirmation prompt.

This setting was necessary because a profile is itself a `.ps1` script. If PowerShell refuses to load scripts, it can refuse to load the profile that defines `roman`.

### Install the fast model

**Script file:** `Install-RAWM.ps1`  
**Command used:**

```powershell
.\Install-RAWM.ps1 -Component fast
```

The installer downloaded the smaller `.gguf` model into the local `models` folder.

### Install all configured components

**Script file:** `Install-RAWM.ps1`  
**Command used:**

```powershell
.\Install-RAWM.ps1 -Component all
```

In this project, `all` means the runtime if it is missing, the fast model if it is missing, and the code model if it is missing. The installer skips a component when the expected file already exists.

### Copy the extracted runtime into the local project

During the setup, a previously extracted runtime was found in a temporary folder. The command used the exact temporary folder that existed on this computer at that moment:

```powershell
Get-ChildItem -LiteralPath 'C:\Users\ROMAN\AppData\Local\Temp\rawm-llama-31e44d9ce25f4553b30731dc7e51bd6c' -Recurse -Filter llama-server.exe |
    ForEach-Object {
        Get-ChildItem -LiteralPath $_.DirectoryName |
            Copy-Item -Destination '.\runtime\llama.cpp' -Recurse -Force
    }
```

This is a historical command. The random-looking folder name was temporary and is not a portable path to rely on later.

Read it from the outside inward:

```text
Find llama-server.exe anywhere below this temporary folder
        |
        v
For each match, inspect its containing directory
        |
        v
Copy that directory's contents into runtime/llama.cpp
```

`ForEach-Object` repeats its block once for each object coming through the pipe. `$_` means “the current object.” `$_ .DirectoryName` in ordinary spacing means the folder containing the current `llama-server.exe` match.

## 5. The launcher: `Start-RAWM.ps1`

**File type:** PowerShell script (`.ps1`)  
**Location:** `Start-RAWM.ps1` in the project root  
**Purpose:** Start the application and pass launch options into it.

The beginning defines parameters:

```powershell
[CmdletBinding()]
param(
    [ValidateSet('auto', 'fast', 'code')]
    [string]$Mode = 'auto',
    [string]$Resume,
    [switch]$New,
    [switch]$NoBanner
)
```

Here is what each piece means:

| Code | Meaning |
|---|---|
| `[CmdletBinding()]` | Gives a script advanced command behavior and common parameter support. |
| `param(...)` | Declares values the script can receive from its caller. |
| `[ValidateSet(...)]` | Rejects mode values other than `auto`, `fast`, or `code`. |
| `[string]$Mode` | Stores mode as text. |
| `$Mode = 'auto'` | Uses automatic routing when no mode is supplied. |
| `[switch]$New` | Creates a true/false option that is true when `-New` is present. |
| `$Resume` | Holds an optional saved-chat identifier. |

The command forms this enables include:

```powershell
.\Start-RAWM.ps1
.\Start-RAWM.ps1 -Mode fast
.\Start-RAWM.ps1 -Mode code
.\Start-RAWM.ps1 -Resume 20260912-232432-43c819
.\Start-RAWM.ps1 -NoBanner
```

The actual file uses the normal PowerShell form `\`. In your PowerShell window, type `.\Start-RAWM.ps1` with one ordinary backslash after the dot.

The script stops on terminating errors:

```powershell
$ErrorActionPreference = 'Stop'
```

PowerShell has several error behaviors. This setting tells the launcher to treat ordinary command errors as stopping errors so a missing module is reported immediately instead of being followed by confusing secondary failures.

### The PowerShell 7 compatibility handoff

The local start script checks the major PowerShell version:

```powershell
if ($PSVersionTable.PSVersion.Major -lt 7) {
    $modernShell = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    $modernShellPath = if ($modernShell) { $modernShell.Source } else {
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    }
    if (-not (Test-Path -LiteralPath $modernShellPath -PathType Leaf)) {
        throw 'RAWM requires PowerShell 7. Install PowerShell 7 and run roman again.'
    }
    $forward = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $MyInvocation.MyCommand.Path, '-Mode', $Mode)
    if ($Resume) { $forward += @('-Resume', $Resume) }
    if ($New) { $forward += '-New' }
    if ($NoBanner) { $forward += '-NoBanner' }
    & $modernShellPath @forward
    return
}
```

This code means:

1. Check whether the current shell is older than PowerShell 7.
2. Find `pwsh.exe`, the PowerShell 7 executable.
3. If the normal command is not found, try the known local runtime path.
4. Build an array of arguments for the new process.
5. Forward the mode and optional switches.
6. Execute the same start script through the newer shell.
7. Return from the older shell's copy of the script.

The `&` is the PowerShell call operator. It says, “execute the command represented by the value that follows.” Since `$modernShellPath` contains a path, `& $modernShellPath @forward` runs that executable with the argument array.

`$MyInvocation.MyCommand.Path` is the path of the current script. Using it lets the script relaunch itself rather than guessing where the project lives.

The handoff is a **process boundary**. The older PowerShell process starts another PowerShell process. The two windows can look like one experience because the child process uses the same console.

### Finding the app root

After the version check, the launcher finds its own directory:

```powershell
$rawmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $rawmRoot 'app\RAWM.psm1'
```

`Split-Path -Parent` removes the filename and keeps the containing folder. `Join-Path` combines pieces using the correct path separator. This is better than hard-coding a full path inside the launcher because the project can live in a different parent folder.

The launcher verifies the module:

```powershell
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "RAWM module is missing: $modulePath"
}
```

`-not` reverses true and false. `Test-Path` returns true when the file exists. `-PathType Leaf` means “the path must be a file.” `throw` stops the launcher and prints the useful path in the error.

Finally, it loads and calls the module:

```powershell
Import-Module $modulePath -Force
Start-RAWMChat -Root $rawmRoot -Mode $Mode -Resume $Resume -New:$New -NoBanner:$NoBanner
```

This is a function call with named parameters. The value of `$Mode` is passed to the module's `-Mode` parameter. For switches, `-New:$New` means “pass the switch as present or absent according to the value of `$New`.”

## 6. Registration: `Register-RAWM.ps1`

**File type:** PowerShell script (`.ps1`)  
**Location:** `Register-RAWM.ps1` in the project root  
**Purpose:** Add a safe, identifiable `roman` launcher to the appropriate PowerShell profiles and create a command fallback.

### Registration parameters

```powershell
[CmdletBinding()]
param([switch]$AllPowerShellEditions)
```

The default behavior targets the current profile. When `-AllPowerShellEditions` is supplied, the script adds both profile locations:

```powershell
$targets = @($PROFILE.CurrentUserCurrentHost)
if ($AllPowerShellEditions) {
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\Microsoft.PowerShell_profile.ps1')
}
$targets = $targets | Select-Object -Unique
```

`$targets` is an array. `+=` adds another value. `Select-Object -Unique` removes duplicates in case the current profile is already one of the explicitly added paths.

The two profile paths matter because Windows PowerShell and PowerShell 7 use different user profile folders:

```text
Windows PowerShell 5.1
    Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1

PowerShell 7
    Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

That is why two profile files on the computer were normal. The original problem was not the number of profiles. The problem was that both had corrupted launcher text.

### Markers make a block replaceable

The script uses clear markers:

```powershell
$begin = '# >>> RAWM portable launcher >>>'
$end = '# <<< RAWM portable launcher <<<'
```

The profile block has this general shape:

```powershell
# >>> RAWM portable launcher >>>
function global:roman {
    # locate Start-RAWM.ps1
    # run it
}
# <<< RAWM portable launcher <<<
```

Markers are useful because a registration script can find the part it owns later. Without markers, an unregistration script would have to guess which function belongs to RAWM.

### The launcher template

The registration script builds the function as text:

```powershell
$template = @'
__BEGIN__
function global:roman {
    $rawmStart = '__START__'
    if (-not (Test-Path -LiteralPath $rawmStart -PathType Leaf)) {
        $rawmStart = Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
            $candidateRoot = Join-Path $_.Root '__FOLDER__'
            $candidateManifest = Join-Path $candidateRoot 'RAWM.portable.json'
            if (Test-Path -LiteralPath $candidateManifest -PathType Leaf) {
                try {
                    $manifest = Get-Content -LiteralPath $candidateManifest -Raw | ConvertFrom-Json
                    if ($manifest.packageId -eq 'rawm-portable-roman-v1') {
                        Join-Path $candidateRoot 'Start-RAWM.ps1'
                    }
                } catch {}
            }
        } | Select-Object -First 1
    }
    if (-not $rawmStart) {
        Write-Host 'RAWM was not found. Connect the portable SSD or run Register-RAWM.ps1 again.' -ForegroundColor Yellow
        return
    }
    & $rawmStart @args
}
__END__
'@
```

The `@' ... '@` form is a **single-quoted here-string**. It lets a script hold multiple lines of text. Because it is single-quoted, PowerShell does not expand `$rawmStart` or `$args` while the template is being created. They remain text that will be interpreted later when the generated function runs.

The placeholders are replaced like this:

```powershell
$block = $template.Replace('__BEGIN__',$begin).Replace('__END__',$end).Replace('__START__',$escapedStart).Replace('__FOLDER__',$relativeFolder)
```

This is a basic form of **code generation**: one script creates a small script block using known values.

The apostrophe in the folder name needs escaping inside a single-quoted PowerShell string:

```powershell
$escapedStart = $startPath.Replace("'", "''")
$relativeFolder = (Split-Path -Leaf $root).Replace("'", "''")
```

In PowerShell, two single quotes inside a single-quoted string represent one literal apostrophe. Therefore:

```powershell
'Rawm''s local LLM'
```

means the actual text:

```text
Rawm's local LLM
```

This is a small detail with a large effect. If the apostrophe were not escaped, PowerShell would think the string ended at `Rawm` and would parse the remaining characters as code.

### Replacing the old block safely

The registration script checks whether the block already exists:

```powershell
if ($existing -match [regex]::Escape($begin)) {
    $pattern = '(?s)' + [regex]::Escape($begin) + '.*' + [regex]::Escape($end)
    $literalBlock = $block.Trim()
    $updated = [regex]::Replace($existing, $pattern, { param($match) $literalBlock })
}
```

Important concepts:

| Expression | Meaning |
|---|---|
| `-match` | Tests whether text matches a regular expression. |
| `[regex]::Escape(...)` | Treats marker characters literally inside the pattern. |
| `(?s)` | Lets the dot in `.*` span newlines. |
| `.*` | Matches everything between the start and end markers. |
| `[regex]::Replace` | Replaces the matched region. |
| `{ param($match) $literalBlock }` | A callback that returns the replacement as literal text. |

The callback matters. A replacement string has special `$` behavior. PowerShell source contains many variables beginning with `$`, so passing generated code as a raw replacement string can cause the replacement engine to interpret pieces of the code. Returning the block from a callback keeps it as replacement data.

This is the type of syntax issue that caused the earlier profile corruption. When code is being inserted into code, there are two interpreters to think about: the generator and the generated script.

### Preserving the old profile

Before writing, the registration script creates a timestamped backup:

```powershell
if (Test-Path -LiteralPath $profilePath) {
    Copy-Item -LiteralPath $profilePath -Destination ($profilePath + '.rawm-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
[IO.File]::WriteAllText($profilePath, $updated, (New-Object Text.UTF8Encoding($false)))
```

`Copy-Item` makes a copy. `Get-Date -Format` creates a readable timestamp. `WriteAllText` writes the final text with UTF-8 encoding and no byte-order mark. This is a direct file write, so it is one of the lines that deserves caution in any script review.

### The `roman.cmd` fallback

The registration script also writes a Windows command file:

```text
@echo off
where pwsh.exe >nul 2>nul
if %errorlevel%==0 (
  pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1" %*
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1" %*
)
```

**File type:** Windows command script (`.cmd`)  
**Location:** `C:\Users\ROMAN\AppData\Local\Microsoft\WindowsApps\roman.cmd`  
**Read by:** `cmd.exe`, invoked when Windows resolves the application command.

The `.cmd` syntax is different from PowerShell:

| `.cmd` syntax | Meaning |
|---|---|
| `@echo off` | Do not echo every command before executing it. |
| `where pwsh.exe` | Search for PowerShell 7. |
| `%errorlevel%` | The last command's status code in the command shell. |
| `%*` | Forward all arguments passed to the `.cmd` file. |
| `>nul 2>nul` | Hide normal and error output from the lookup. |
| Parentheses | Group the `if` branch commands. |

The PowerShell profile function uses `@args`. The `.cmd` file uses `%*`. They both mean “pass along what the caller supplied,” but they belong to different languages.

## 7. The main application: `app/RAWM.psm1`

**File type:** PowerShell module (`.psm1`)  
**Location:** `app/RAWM.psm1`  
**Purpose:** Hold the reusable functions that make RAWM operate.

The file begins with strict behavior:

```powershell
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
```

`Set-StrictMode` makes certain accidental mistakes fail earlier, such as reading variables that were never created. Strict mode can expose bugs that a looser script might silently ignore.

The module also creates shared state:

```powershell
$script:Root = $null
$script:Settings = $null
$script:Session = $null
$script:Mode = 'auto'
$script:ActiveModelMode = $null
$script:ServerProcess = $null
$script:LastAnswer = ''
$script:LastUsage = $null
```

The `script:` scope means these values belong to the module script and can be used by its functions. `$null` means “no value yet.” The state is not the same as saved data: it lives in memory until the app saves the session.

### PowerShell function anatomy

A RAWM function generally looks like this:

```powershell
function Get-RAWMModelConfig {
    param([ValidateSet('fast','code')][string]$ModelMode)

    $entry = $script:Settings.models.$ModelMode
    $path = Join-Path $script:Root ([string]$entry.file)

    [pscustomobject]@{
        Mode        = $ModelMode
        Name        = [string]$entry.name
        Path        = $path
        MaxTokens   = [int]$entry.maxTokens
        Temperature = [double]$entry.temperature
    }
}
```

Read it in order:

1. Define a function named `Get-RAWMModelConfig`.
2. Accept one text parameter named `$ModelMode`.
3. Look up that mode in the settings object.
4. Build the absolute model path.
5. Return a structured object containing the values other functions need.

The verb `Get` is a clue that the function returns information. The `RAWM` part groups the project's functions. The final noun describes the result.

`[pscustomobject]@{ ... }` creates an object with named properties. This is better than returning one long string because later code can ask for `$model.Path` or `$model.MaxTokens` directly.

## 8. Routing code: how `auto`, `fast`, and `code` work

The routing function is intentionally small:

```powershell
function Get-RAWMModelMode {
    param([string]$InputText)

    if ($script:Mode -in @('fast','code')) { return $script:Mode }

    $codePattern = '(?i)\b(write|implement|build|create|refactor|debug|fix|code|script|function|class|module|api|regex|powershell|python|javascript|typescript|sql|html|css|compile|stack trace|exception)\b'
    if ($InputText -match $codePattern -or $InputText -match '```') { return 'code' }

    return 'fast'
}
```

This function has three decisions:

```text
Was a manual mode selected?
       |
  yes  |  no
       |         Check for coding words or a fenced code block
       |                         |
       v                    yes | no
    use it                  code | fast
```

The regular expression pieces mean:

| Piece | Meaning |
|---|---|
| `(?i)` | Ignore upper/lowercase differences. |
| `\b` | Word boundary. Prevents a keyword from matching inside a larger word in many cases. |
| `(a|b|c)` | Match one of the alternatives. |
| `-match` | Ask whether the text matches the pattern. |
| `-in @('fast','code')` | Ask whether the current value appears in the allowed list. |
| `return` | Send a value back to the caller immediately. |

This is a rule-based router, not a second AI model. It is fast because it only checks text. It is also limited: the message “write a birthday poem” contains `write`, so the current rules send it to Code. That is an example of a feature that is working exactly as coded while still being a possible future refinement.

Manual mode commands are handled in `Invoke-RAWMCommand`:

```powershell
'/auto' { $script:Mode='auto'; Write-RAWMColor 'Routing: AUTO' Green }
'/fast' { $script:Mode='fast'; Write-RAWMColor 'Routing: FAST' Green }
'/code' { $script:Mode='code'; Write-RAWMColor 'Routing: CODE' Green }
```

These entries appear inside a `switch` statement. A `switch` compares a value against possible cases. The string on the left is the case; the braces contain the work performed for that case.

## 9. Starting the local inference server

The selected model is started only when an actual answer is requested.

First, RAWM checks whether the server is healthy:

```powershell
function Test-RAWMServer {
    try {
        $uri = "http://$($script:Settings.backend.host):$($script:Settings.backend.port)/health"
        $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 2
        return ($response.status -in @('ok','no slot available'))
    } catch { return $false }
}
```

`try` attempts the request. `catch` handles a failure and returns false. The `$(...)` inside the double-quoted URI performs an expression and inserts its result into the text. The URI becomes:

```text
http://127.0.0.1:18080/health
```

The server is local because `127.0.0.1` means “this computer.” Port `18080` is the numbered destination where the local engine listens.

The start routine builds the model and server paths:

```powershell
$model = Get-RAWMModelConfig $ModelMode
$server = Join-Path $script:Root 'runtime\llama.cpp\llama-server.exe'

if (-not (Test-Path -LiteralPath $model.Path -PathType Leaf)) {
    throw "The $ModelMode model is not installed. Run .\Install-RAWM.ps1."
}

if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
    throw "The local inference runtime is not installed. Run .\Install-RAWM.ps1."
}
```

Then it starts the executable in a hidden window and redirects logs:

```powershell
$logFolder = Join-Path $script:Root 'data\logs'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
$stdout = Join-Path $logFolder 'llama-server.out.log'
$stderr = Join-Path $logFolder 'llama-server.err.log'

$script:ServerProcess = Start-Process `
    -FilePath $server `
    -ArgumentList $args `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr
```

The backtick at the end of a line continues a PowerShell command onto the next line. It is a line-continuation character. The actual code in the project uses one long line for `Start-Process`; this expanded version is formatted for teaching.

`-PassThru` returns a process object, which RAWM stores in `$script:ServerProcess`. That gives the app a handle it can use later to check or stop the process.

The start routine waits for the health endpoint:

```powershell
$deadline = (Get-Date).AddSeconds([int]$script:Settings.backend.startupTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if ($script:ServerProcess.HasExited) {
        $detail = if (Test-Path $stderr) {
            (Get-Content -LiteralPath $stderr -Tail 12) -join "`n"
        } else {
            'No server log was produced.'
        }
        throw "llama-server stopped during startup.`n$detail"
    }
    if (Test-RAWMServer) { $script:ActiveModelMode = $ModelMode; return }
    Start-Sleep -Milliseconds 300
}
```

This is a polling loop. It asks “is the server ready?” repeatedly until the deadline. The short sleep prevents it from asking thousands of times per second.

The backtick followed by `n` inside a string means newline. `-join "`n"` combines multiple log lines into one error message.

## 10. Sending a chat request

The local application uses an HTTP request to ask the running server for a response.

The request body is assembled as a PowerShell hashtable and converted to JSON:

```powershell
$body = @{
    model = $model.Name
    messages = @($script:Session.messages)
    stream = $true
    stream_options = @{ include_usage = $true }
    max_tokens = $model.MaxTokens
    temperature = $model.Temperature
    chat_template_kwargs = @{ enable_thinking = $false }
} | ConvertTo-Json -Depth 12 -Compress
```

This is PowerShell data syntax, not JSON syntax. PowerShell uses `@{}` for a hashtable, and can use `$true` and `$false`. `ConvertTo-Json` translates it into JSON before it is sent.

The request is sent here:

```powershell
$uri = "http://$($script:Settings.backend.host):$($script:Settings.backend.port)/v1/chat/completions"
$client = New-Object Net.Http.HttpClient
$request = New-Object Net.Http.HttpRequestMessage([Net.Http.HttpMethod]::Post, $uri)
$request.Content = New-Object Net.Http.StringContent($body, [Text.Encoding]::UTF8, 'application/json')
$response = $client.SendAsync(
    $request,
    [Net.Http.HttpCompletionOption]::ResponseHeadersRead
).GetAwaiter().GetResult()
```

The actual file keeps the method call on one line; this version is split for readability.

| Code | Meaning |
|---|---|
| `HttpClient` | A .NET object able to make HTTP requests. |
| `HttpRequestMessage` | A request object containing method, address, and content. |
| `Post` | Send data to the server. |
| `StringContent` | Put the JSON text into the request body. |
| `UTF8` | Text encoding used for the body. |
| `application/json` | Tell the server what format the body uses. |
| `ResponseHeadersRead` | Begin reading as the response arrives instead of waiting for the entire answer. |
| `GetAwaiter().GetResult()` | Wait synchronously for the .NET task's result. |

The local server presents a chat-completions style endpoint. The presence of an HTTP API does not mean the request is going to the internet; this URL points to loopback on the same computer.

## 11. Streaming the response

The request asks for `stream = $true`. The server then sends multiple event lines rather than one giant response. RAWM reads them with a `StreamReader`:

```powershell
$stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
$reader = New-Object IO.StreamReader($stream)

while (-not $reader.EndOfStream) {
    $line = $reader.ReadLine()
    if (-not $line.StartsWith('data:')) { continue }

    $data = $line.Substring(5).Trim()
    if ($data -eq '[DONE]') { break }
    if (-not $data) { continue }

    $event = $data | ConvertFrom-Json
    # read usage and content from $event
}
```

This loop says:

1. Continue while the response stream has more lines.
2. Read one line.
3. Ignore lines that are not data events.
4. Remove the `data:` prefix.
5. Stop at the special `[DONE]` marker.
6. Convert the event's JSON into a PowerShell object.

When a content piece exists, RAWM appends it to the answer and displays it:

```powershell
$safe = Remove-RAWMControlSequence ([string]$piece)
[void]$builder.Append($safe)
Write-RAWMWrappedText -Text $safe -State $wrapState
```

There are two paths here:

```text
$safe --------------------> StringBuilder -> saved final answer
       \
        +------------------> wrapped display -> your screen
```

That separation matters. The screen may receive display line breaks, but the stored answer remains a separate accumulated value. `/copy` and `/export` use the accumulated answer rather than rebuilding it from the visible console.

The cleanup code runs even when the request fails:

```powershell
finally {
    if ($reader) { $reader.Dispose() }
    if ($stream) { $stream.Dispose() }
    if ($response) { $response.Dispose() }
    $request.Dispose()
    $client.Dispose()
}
```

`Dispose()` releases .NET resources such as streams and network objects. The `finally` block is a cleanup promise: try the work, handle errors if needed, and release resources at the end.

## 12. Word wrapping code

This feature was added because long streamed lines went beyond the visible PowerShell window.

**File type:** PowerShell module (`.psm1`)  
**File:** `app/RAWM.psm1`  
**Functions:** `Get-RAWMTextWidth` and `Write-RAWMWrappedText`

### Measuring the window

```powershell
function Get-RAWMTextWidth {
    $visibleWidth = 80
    try {
        if ([Console]::WindowWidth -gt 0) {
            $visibleWidth = [Console]::WindowWidth
        }
    } catch {}
    return [Math]::Max(1, $visibleWidth - 1)
}
```

The fallback width is 80. If the console reports a positive width, the code uses it and subtracts one column as a margin. `[Console]::WindowWidth` is a .NET static property. The `::` syntax accesses a static member on a type.

The `try/catch` protects the app in environments where a normal console width cannot be queried.

### Buffering streamed words

The response server may split a word between two events. The wrapper therefore maintains state:

```powershell
$wrapState = @{ Pending=''; Column=0 }
```

`Pending` holds unfinished display text. `Column` records the current visible column.

The wrapper begins like this:

```powershell
function Write-RAWMWrappedText {
    param([string]$Text, [hashtable]$State, [switch]$Flush)

    $State.Pending += $Text.Replace("`r", '').Replace("`t", '    ')
```

Carriage returns are removed for consistent display. Tabs become four spaces. The text is appended to the pending buffer.

The token pattern separates newlines, whitespace, and non-whitespace text:

```powershell
$match = [regex]::Match($State.Pending, '^(\n|[^\S\n]+|[^\s]+)')
$token = $match.Value
```

The pattern is a little dense, so the intention is more useful than memorizing it:

```text
newline       -> finish this screen line
spaces        -> preserve spacing when possible
non-space text -> a word or a piece of a long word
```

If the app has only received part of a short word and has not been told to flush, it waits:

```powershell
if (-not $Flush -and
    $token -notmatch '\s' -and
    $token.Length -eq $State.Pending.Length -and
    $token.Length -lt $width) {
    break
}
```

That prevents a network piece ending in `str` from immediately being treated as a complete word when the next piece may begin with `eaming`.

When a token would not fit, the wrapper starts a new line:

```powershell
if ($token -notmatch '^\s+$' -and
    $State.Column -gt 0 -and
    ($State.Column + $token.Length) -gt $width) {
    Write-Host
    $State.Column = 0
}
```

For a very long unbroken string, it prints the token in chunks no wider than the available space:

```powershell
while ($token.Length -gt 0) {
    $available = $width - $State.Column
    if ($available -le 0) {
        Write-Host
        $State.Column = 0
        $available = $width
    }
    $count = [Math]::Min($available, $token.Length)
    Write-Host $token.Substring(0, $count) -NoNewline
    $State.Column += $count
    $token = $token.Substring($count)
}
```

This is a classic loop that consumes a string piece by piece. `Substring(0, $count)` takes the beginning portion. Assigning the shorter remainder back to `$token` lets the loop continue.

At the end of the response, the app flushes the last pending text:

```powershell
Write-RAWMWrappedText -Text '' -State $wrapState -Flush
Write-Host
```

The `-Flush` switch means no more streamed pieces are expected. Without it, a final word with no following whitespace might remain in the buffer.

### The wrapper does not rewrite the saved answer

This line stores the raw safe response:

```powershell
[void]$builder.Append($safe)
```

This line controls how it appears on screen:

```powershell
Write-RAWMWrappedText -Text $safe -State $wrapState
```

That design keeps display formatting separate from saved content. It is a small example of a good application habit: do not use a presentation transformation as the source of truth for your data.

## 13. The chat loop

The public function at the bottom of the module is `Start-RAWMChat`.

It prepares the root and settings:

```powershell
$script:Root = (Resolve-Path -LiteralPath $Root).Path
$script:Settings = Read-RAWMJson (Join-Path $script:Root 'config\settings.json')
$script:Mode = $Mode
```

`Resolve-Path` turns the supplied location into a resolved path. `Read-RAWMJson` is a project helper that reads the file and pipes it through `ConvertFrom-Json`.

It creates or resumes a session:

```powershell
if ($Resume) {
    Resume-RAWMSession $Resume
} else {
    New-RAWMSession
}
```

Then the central loop waits for input:

```powershell
while ($true) {
    Write-Host
    Write-RAWMColor 'roman > ' Cyan -NoNewline
    $inputText = [Console]::ReadLine()
    if ($null -eq $inputText) { break }
    if (-not $inputText.Trim()) { continue }

    # handle slash commands or send a normal message
}
```

`while ($true)` repeats forever until `break`. `continue` skips the rest of the current loop and asks for another line. `[Console]::ReadLine()` reads from the current terminal.

The application treats a line beginning with `/` as an internal command. Otherwise it:

```powershell
$modelMode = Get-RAWMModelMode $inputText
Add-RAWMMessage 'user' $inputText
Save-RAWMSession
$answer = Invoke-RAWMCompletion $modelMode
Add-RAWMMessage 'assistant' $answer
Save-RAWMSession
```

That sequence is the core product behavior:

```text
read input
   |
   v
choose mode
   |
   v
save user message
   |
   v
ask local model
   |
   v
save assistant answer
```

If a request fails, the catch block removes the just-added user message when appropriate, saves the remaining session, and prints the error. That prevents a failed request from leaving the conversation state in a misleading half-complete condition.

When the app exits, its `finally` block saves the session, stops the server process it owns, and prints a closing message.

## 14. Settings: `config/settings.json`

**File type:** JSON data (`.json`)  
**File:** `config/settings.json`  
**Purpose:** Give the application named values without hard-coding every setting in the module.

The backend section is:

```json
{
  "backend": {
    "type": "llama.cpp",
    "host": "127.0.0.1",
    "port": 18080,
    "contextSize": 4096,
    "gpuLayers": "auto",
    "startupTimeoutSeconds": 300
  }
}
```

JSON rules to notice:

| JSON item | Meaning |
|---|---|
| `{ ... }` | An object containing named properties. |
| `"backend"` | A property name; JSON names use double quotes. |
| `:` | Separates a property name from its value. |
| `,` | Separates properties. |
| `18080` | A number. |
| `"llama.cpp"` | A text string. |
| `true` / `false` | Boolean values. |

JSON does not use PowerShell's `$true`, single-quoted strings, or comments. A JSON parser reads punctuation exactly. A missing comma can make an otherwise understandable file invalid.

The model section connects friendly mode names to real files:

```json
{
  "models": {
    "fast": {
      "name": "Qwen3.5 0.8B Q4_K_M",
      "file": "models/Qwen3.5-0.8B-Q4_K_M.gguf",
      "maxTokens": 384,
      "temperature": 0.25
    },
    "code": {
      "name": "Qwen3.5 4B Q4_K_M",
      "file": "models/Qwen3.5-4B-Q4_K_M.gguf",
      "maxTokens": 2048,
      "temperature": 0.15
    }
  }
}
```

The application combines the project root with each relative `file` value. This is why the settings file can say `models/...` while the code still finds the actual C-drive location.

The mode names are application labels. `fast` means the smaller model and `code` means the larger model in this project. The name `code` does not automatically guarantee that the model is a specialized coding model.

## 15. Behavior instructions: `context/RAWM-BEHAVIOR.md`

**File type:** Markdown (`.md`)  
**File:** `context/RAWM-BEHAVIOR.md`  
**Purpose:** Store natural-language behavior instructions that are inserted as the system message of a new chat.

The current file begins like this:

```markdown
# RAWM behavior

You are RAWM, Roman's local assistant.

- Answer directly.
- Default to one to three short sentences unless the request needs more detail.
- Prioritize useful, correct code when code is requested.
```

When `New-RAWMSession` runs, it reads this file:

```powershell
$behavior = Get-Content -LiteralPath (Join-Path $script:Root 'context\RAWM-BEHAVIOR.md') -Raw -Encoding UTF8
```

Then it creates a message with a `system` role:

```powershell
messages = [System.Collections.ArrayList]@(
    [pscustomobject]@{ role = 'system'; content = $behavior }
)
```

The Markdown file is not executable. It becomes meaningful because the PowerShell module reads it and passes its text to the model.

This is a central software lesson: a file's effect depends on the code that consumes it. A `.md` file can be documentation, model context, a project note, or unused text depending on who reads it.

## 16. Sessions and JSON save files

`New-RAWMSession` makes a session object:

```powershell
$now = Get-Date
$id = $now.ToString('yyyyMMdd-HHmmss') + '-' + ([guid]::NewGuid().ToString('N').Substring(0, 6))

$script:Session = [pscustomobject]@{
    schemaVersion = 1
    id = $id
    title = 'New chat'
    createdAt = $now.ToString('o')
    updatedAt = $now.ToString('o')
    messages = [System.Collections.ArrayList]@(
        [pscustomobject]@{ role = 'system'; content = $behavior }
    )
    totals = [pscustomobject]@{
        promptTokens = 0
        completionTokens = 0
        turns = 0
    }
}
```

The timestamp makes the file easier to sort. The GUID suffix reduces the chance that two sessions created in the same second receive the same identifier.

Saving uses a temporary file:

```powershell
$path = Join-Path $folder ($script:Session.id + '.json')
$temp = "$path.tmp"
$json = $script:Session | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText($temp, $json, (New-Object Text.UTF8Encoding($false)))
Move-Item -LiteralPath $temp -Destination $path -Force
```

The idea is:

```text
session object in memory
        |
        v
ConvertTo-Json
        |
        v
write temporary .tmp file
        |
        v
move it into final .json name
```

The temporary write lowers the chance that the final file is left half-written if the process is interrupted during the write. It is not a complete backup system.

The saved file contains messages and usage totals. It does not contain the model's learned weights, and the conversation does not retrain the model.

## 17. Slash commands and `switch`

`Invoke-RAWMCommand` parses a line such as `/copy code`:

```powershell
$parts = $InputText.Trim().Split(@(' '), 2, [StringSplitOptions]::RemoveEmptyEntries)
$command = $parts[0].ToLowerInvariant()
$argument = if ($parts.Count -gt 1) { $parts[1] } else { '' }
```

The first piece becomes the command. The second piece becomes an optional argument. `ToLowerInvariant()` makes `/HELP` and `/help` behave consistently.

Then a `switch` chooses an action:

```powershell
switch ($command) {
    '/help'   { Show-RAWMHelp }
    '/new'    { New-RAWMSession }
    '/model'  { Show model information }
    '/export' { $path = Export-RAWMSession }
    '/exit'   { return [pscustomobject]@{ Handled=$true; Exit=$true } }
    default   { Write-RAWMColor "Unknown command: $command. Use /help." Amber }
}
```

The phrase `Show model information` above is explanatory pseudocode, not valid code. In the actual file, the `/model` branch calls `Get-RAWMModelConfig`, checks `Test-Path`, and writes a box. This is an important documentation habit: label pseudocode clearly so a reader does not copy it expecting it to run.

The `/exit` branch returns a small object with an `Exit` property. The outer chat loop checks that property and breaks. This lets the inner command function communicate a decision to the outer loop without directly controlling the entire application.

## 18. Copying code and exporting Markdown

The app can copy the last answer or the first fenced code block.

The code-block extractor uses a regular expression:

```powershell
$match = [regex]::Match($Text, '(?s)```[^\r\n]*\r?\n(.*?)```')
if ($match.Success) {
    return $match.Groups[1].Value.TrimEnd()
}
return $null
```

The pattern looks for an opening triple-backtick fence, an optional language label, a newline, the body, and a closing fence. `(?s)` lets the body span newlines.

The clipboard code uses whichever command is available:

```powershell
if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
    Set-Clipboard -Value $Text
    return
}
$Text | clip.exe
```

The fallback pipes the text to Windows' `clip.exe`. A pipe does not always mean network communication. Here it simply passes text from one local command to another.

Conversation export writes a Markdown file:

```powershell
$path = Join-Path $folder ($script:Session.id + '.md')
$sb = New-Object Text.StringBuilder
[void]$sb.AppendLine("# $($script:Session.title)")

foreach ($message in $script:Session.messages) {
    if ($message.role -eq 'system') { continue }
    [void]$sb.AppendLine()
    [void]$sb.AppendLine("## $($message.role)")
    [void]$sb.AppendLine()
    [void]$sb.AppendLine([string]$message.content)
}

[IO.File]::WriteAllText($path, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
```

The system message is skipped so the exported conversation is focused on the user and assistant exchange. The output extension is `.md` because the export contains Markdown headings and plain conversation text.

## 19. The installer: `Install-RAWM.ps1`

**File type:** PowerShell script (`.ps1`)  
**Purpose:** Download the runtime and model files when they are missing.

Its component parameter is restricted:

```powershell
param(
    [ValidateSet('runtime','fast','code','all')]
    [string]$Component = 'all'
)
```

The downloader uses a partial destination:

```powershell
$partial = "$Destination.partial"
```

That naming convention distinguishes an unfinished file from a completed model. It can resume with `curl.exe`:

```powershell
& $curl.Source '--location' '--fail' '--retry' '8' '--retry-all-errors' '--retry-delay' '5' '--continue-at' '-' '--output' $partial $Uri
```

The `&` runs the command stored in `$curl.Source`. The arguments are separate array items, which helps PowerShell pass paths and options without merging them accidentally.

After a successful download:

```powershell
Move-Item -LiteralPath $partial -Destination $Destination -Force
```

The installer moves the partial file into the final filename. The actual models are binary data, so they are not readable like the scripts in this guide.

The runtime installer asks GitHub for release information, chooses an x64 Windows CPU package, expands its ZIP archive, and copies the required executable and libraries into `runtime/llama.cpp`. This is dependency installation: the application relies on an external engine to perform inference.

## 20. Profiles, policy, and parser errors in code terms

A profile is a startup `.ps1` file. When PowerShell opens, it attempts to load the profile that belongs to that shell and host. The profile defines `roman` as a function.

The earlier failure had two different categories of problem:

```text
Category A: policy / loading problem
PowerShell refuses to load the profile or script.

Category B: parser problem
PowerShell reads the file but cannot understand its braces, quotes, or pipeline structure.
```

The screenshot showed parser errors such as an unexpected closing brace and an empty pipe element. That meant PowerShell had reached the file and was trying to parse it. The profile content itself was malformed because launcher blocks had been duplicated inside one another.

The profile was intended to contain one clean block like this:

```powershell
# >>> RAWM portable launcher >>>
function global:roman {
    $rawmStart = 'C:\Users\ROMAN\Documents\ChatGPT\Rawm''s local LLM\Start-RAWM.ps1'
    & $rawmStart @args
}
# <<< RAWM portable launcher <<<
```

The parser needs to match:

```text
function starts       {
function body         ...
function ends         }
launcher block ends   marker
```

When another `function` begins in the middle of an unfinished expression, or a pipe appears with no valid command on one side, the parser cannot create the intended structure.

Execution policy is a separate gate. `Restricted` can prevent `.ps1` scripts and profiles from running at all. `RemoteSigned` allows local scripts while applying signature rules to downloaded scripts. `Bypass` tells a child launch to skip policy blocking for that invocation. Policy scopes and organization settings can affect which value wins.

The commands to recognize are:

```powershell
Get-ExecutionPolicy -List
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

The first reads. The second changes the current user's setting.

Useful official references:

- [PowerShell profiles](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles?view=powershell-7.5)
- [PowerShell execution policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.5)
- [PowerShell quoting rules](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules?view=powershell-7.5)

## 21. Testing commands and what each test proved

Tests were run through the real entry paths instead of only importing functions.

### Fast response test

**Input file:** `tests/smoke-input.txt`  
**Command:**

```powershell
Get-Content tests\smoke-input.txt | powershell.exe -Command roman
```

The input file contained a short greeting request followed by `/exit`. The pipe supplied those lines to the normal `roman` command. This proved that the launcher could open RAWM, choose Fast, generate a response, and close.

### Code response test

**Input file:** `tests/code-smoke-input.txt`  
**Command:**

```powershell
Get-Content tests\code-smoke-input.txt |
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-RAWM.ps1
```

This direct test bypassed profile loading and tested the start script itself. The input requested a short `Get-Greeting` function and then `/exit`. It proved that the larger model could load and return code.

### Normal user-path test

The final check used the command a user would actually type:

```powershell
Get-Content tests\smoke-input.txt | powershell.exe -Command roman
```

The observed result included the RAWM banner, a Fast response, usage information, and the closing message.

### Word-wrap test

The wrapping helper was tested with text pieces that intentionally arrived in awkward chunks:

```text
This is a str
eaming response with words and
averylongunbrokenstringthatmustwrap
newline and indentation
```

The test checked that simulated 20-column output did not exceed the width and that the text content was not lost. This was a focused helper test; it was not a visual test of every terminal font or every possible wide Unicode character.

The general testing lesson is:

```text
unit behavior test        -> test one helper
direct launch test        -> test Start-RAWM.ps1
normal entry test         -> test what the user types
real model response       -> prove the dependency works too
```

## 22. A code-reading strategy for future edits

When you want to understand a feature, trace it from the visible action backward and forward.

Example: “I want to change how `/copy code` works.”

```text
/copy code
   |
   v
Invoke-RAWMCommand
   |
   v
Get-RAWMCodeBlock
   |
   v
Set-RAWMClipboard
```

Then ask:

1. What input enters the first function?
2. What value does each function return?
3. Is the value text, an object, a path, or a process?
4. Which file is read or written?
5. What happens if the expected value is missing?

Example: “I want to change automatic routing.”

```text
normal message
   |
   v
Start-RAWMChat
   |
   v
Get-RAWMModelMode
   |
   +--> return fast
   |
   +--> return code
   |
   v
Invoke-RAWMCompletion
```

Example: “I want to change the model's response length.”

```text
config/settings.json
   |
   v
Get-RAWMModelConfig
   |
   v
Invoke-RAWMCompletion
   |
   v
max_tokens in the JSON request
```

This is called tracing a **data flow**. You follow the value from where it begins to where it changes behavior.

## 23. Common syntax mistakes to recognize

### Wrong language in the wrong file

```text
JSON file:       "port": 18080
PowerShell:      $port = 18080
```

These are both valid in their own languages. Neither should be copied into the other file without translation.

### Missing quote

```powershell
$name = 'RAWM
```

PowerShell keeps looking for the closing quote. The error may appear on a later line because the parser does not realize the mistake until the rest of the file no longer fits the expected structure.

### Missing brace

```powershell
function Example {
    Write-Host 'Hello'
```

The function needs a closing `}`. Editors often help by indenting matching blocks.

### Pipeline with no command

```powershell
Get-Content file.txt |
```

The pipe needs a command after it, such as `ConvertFrom-Json` or `Where-Object`. An empty pipe element is a parser error.

### Wrong variable spelling

```powershell
$rawmStart = '...'
& $rawmstart
```

PowerShell variable names are generally case-insensitive, but spelling errors that change the name are still problems. Strict mode can help reveal missing variables.

### A path with spaces not treated as one value

```powershell
Start-Process C:\Users\ROMAN\Documents\ChatGPT\Rawm's local LLM\Start-RAWM.ps1
```

The spaces divide the path into multiple arguments. A quoted path or a variable holding the path is safer:

```powershell
$startPath = 'C:\Users\ROMAN\Documents\ChatGPT\Rawm''s local LLM\Start-RAWM.ps1'
& $startPath
```

## 24. Commands you can use as a learner

These are useful inspection commands. They do not edit the application.

```powershell
# What PowerShell am I using?
$PSVersionTable.PSVersion

# Which profile belongs to this session?
$PROFILE

# What profiles are known in this session?
$PROFILE | Select-Object *

# What does roman resolve to?
Get-Command roman -All

# Where am I?
Get-Location

# What is inside this folder?
Get-ChildItem -Force

# Does a file exist?
Test-Path -LiteralPath '.\app\RAWM.psm1' -PathType Leaf

# Read JSON as a PowerShell object
Get-Content '.\config\settings.json' -Raw | ConvertFrom-Json

# Find a function name in the source
rg -n 'function Get-RAWM|function Start-RAWM|Write-RAWMWrappedText' .
```

The comments beginning with `#` are for people. PowerShell ignores them when it runs the commands.

## 25. The honest description of your coding role

You supplied the product direction and the testing priorities. You described the desired behavior in ordinary language, noticed when the experience was not acceptable, provided the screenshot and error evidence, decided that the local C-drive version came first, and asked for readability improvements.

The AI coding assistant translated those requirements into PowerShell code, inspected files, made the local changes, and tested them. Existing tools supplied additional building blocks: PowerShell, the llama.cpp runtime, and Qwen model files.

That is real software development work. It is also accurate to say that you used AI as a coding partner rather than claiming that you personally wrote every line from memory. A product builder's work includes deciding what to build, defining constraints, evaluating results, and iterating until the experience works.

The useful vocabulary you gained from this project includes:

```text
requirements     -> what you want the product to do
scope             -> which version or files are allowed to change
entry point       -> where the user begins
launcher          -> code that starts the main program
module            -> reusable group of functions
dependency        -> external component the app needs
configuration     -> values that control behavior
state             -> information held while running
persistence       -> information saved after closing
parser error      -> source text is not structurally valid
runtime error     -> valid code failed while running
test              -> evidence for a behavior
debugging         -> finding and correcting a cause
```

## 26. A reusable prompt for your next coding project

When you start another project, you can give an AI coding partner a request like this:

```text
I want to build [describe the experience in plain English].

Please first map the project into:
- entry point
- main application logic
- configuration
- saved data
- external dependencies
- tests

For every file you create or change, tell me:
- the exact filename and extension
- which language or format reads it
- what responsibility belongs there
- what the important functions do
- how I can test it as a user

Keep these boundaries:
- only change [the allowed folder or files]
- preserve [the things that must not change]
- explain syntax in beginner-friendly terms
- show the exact command I should type
- distinguish pseudocode from code that can actually run

Do not say it works until the real user entry point has been tested.
```

That prompt turns your natural-language product thinking into a technical handoff while keeping the explanation accessible.

## 27. Quick reference: what to open first

```text
Want to understand the command?
    Open the profile or roman.cmd

Want to understand startup?
    Open Start-RAWM.ps1

Want to understand chat behavior?
    Open app/RAWM.psm1

Want to understand routing?
    Search Get-RAWMModelMode

Want to understand model settings?
    Open config/settings.json

Want to understand the local assistant's style?
    Open context/RAWM-BEHAVIOR.md

Want to understand saved chats?
    Search New-RAWMSession, Save-RAWMSession, Resume-RAWMSession

Want to understand word wrapping?
    Search Get-RAWMTextWidth and Write-RAWMWrappedText

Want to understand a startup failure?
    Run Get-Command roman -All
    Run Get-ExecutionPolicy -List
    Read the first red parser error
```

The first red error is usually more useful than the last red error. Later errors can be consequences of the parser already being confused by an earlier missing quote, brace, or command.

## 28. Final file map

```text
LOCAL RAWM PROJECT
|
+-- Start-RAWM.ps1
|      PowerShell entry script (.ps1)
|
+-- Register-RAWM.ps1
|      Profile and fallback registration script (.ps1)
|
+-- Unregister-RAWM.ps1
|      Removes RAWM's marked registration block (.ps1)
|
+-- Install-RAWM.ps1
|      Downloads runtime and models (.ps1)
|
+-- app/RAWM.psm1
|      Main reusable PowerShell module (.psm1)
|
+-- config/settings.json
|      Model and interface values (.json)
|
+-- context/RAWM-BEHAVIOR.md
|      Natural-language system instructions (.md)
|
+-- models/*.gguf
|      Binary model files (.gguf)
|
+-- runtime/llama.cpp/*
|      Inference executable and libraries (.exe/.dll)
|
+-- data/chats/*.json
|      Saved conversations (.json)
|
+-- data/logs/*.log
|      Local diagnostic output (.log)
|
+-- exports/*.md
|      Exported conversations (.md)
|
+-- tests/*.txt
|      Input lines used by smoke tests (.txt)
|
+-- docs/RAWM-CODING-WALKTHROUGH.md
       This coding explanation (.md)
```

The project is understandable as a set of conversations between file types: PowerShell reads scripts, JSON supplies structured values, Markdown supplies human or model-readable instructions, the compiled engine reads the model file, and the saved JSON records preserve the chat state.

That is the coding foundation underneath the experience you designed: a clear entry point, small components with named responsibilities, data moving between them, and tests that check the experience from the user's point of view.
