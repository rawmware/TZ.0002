# RAWM in a Codex terminal

## Engineer-to-engineer implementation guide

This document explains the workflow shown in Roman's screenshot:

```text
Codex desktop is open
        |
        v
A terminal panel is open at the bottom
        |
        v
The terminal is running Windows PowerShell
        |
        v
Roman types: roman
        |
        v
RAWM opens in that same terminal
        |
        +------------------------------+
        |                              |
        v                              v
Codex remains available          RAWM runs a separate
for coding work                  local AI conversation
```

The result feels like two different AI conversations living side by side. Codex remains the engineering workspace, while RAWM is a separate local chat application inside the terminal surface.

The implementation described here is the local Windows version in:

```text
C:\Users\ROMAN\Documents\ChatGPT\Rawm's local LLM
```

The E-drive version is outside this document's scope.

## The architectural fact that makes this work

RAWM was not inserted into Codex's internal user interface. The successful workflow comes from **co-location**:

1. Codex provides a terminal surface.
2. That terminal runs on the same Windows computer.
3. Windows PowerShell resolves the `roman` command.
4. The command starts RAWM in the terminal process area.
5. RAWM runs its own model and conversation loop.
6. Codex continues running in its own application context.

The two systems can appear together on the screen without sharing a conversation, model context, token budget, or internal API.

```text
+-------------------------------------------------------------+
| CODEX DESKTOP                                               |
|                                                             |
|  Codex conversation / review / coding agent                  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | TERMINAL SURFACE                                     |  |
|  |                                                       |  |
|  | Windows PowerShell                                   |  |
|  |                                                       |  |
|  | PS C:\Users\ROMAN> roman                              |  |
|  |                                                       |  |
|  | RAWM terminal application                             |  |
|  |                                                       |  |
|  +-------------------------------------------------------+  |
|                                                             |
+-------------------------------------------------------------+
```

The screenshot proves the visible user experience. It does not prove undocumented details about Codex's internal terminal implementation. An engineer reproducing this workflow should integrate with a host application's supported terminal or shell surface rather than depending on private UI internals.

OpenAI's official documentation includes a local-shell tool category for applications that need local command execution. That is related background, but it should not be interpreted as proof that this RAWM workflow is a direct Codex plugin or MCP integration: [OpenAI local shell documentation](https://developers.openai.com/api/docs/guides/tools-local-shell).

## What the user experiences

```text
1. Open Codex.
2. Open or use the terminal panel.
3. Type roman.
4. RAWM displays its banner.
5. Type a message at roman >.
6. RAWM selects a local model.
7. The local answer streams into the terminal.
8. Codex remains available above it.
```

The phrase “type a passcode and talk to another AI” describes the feeling, but `roman` is technically a command name, not authentication. It does not verify a password or create a security boundary. It is a memorable entry point for a local program.

The two conversations are separate:

| Property | Codex conversation | RAWM conversation |
|---|---|---|
| Host | Codex desktop workspace | Terminal process hosted in the Codex window |
| Model | Codex model selected by the Codex environment | Local Qwen model selected by RAWM |
| Context | Codex task history and workspace context | RAWM saved messages and behavior file |
| Token accounting | Codex account usage rules | Local inference counters shown by RAWM |
| Tools | Codex tools and workspace integrations | PowerShell functions and local `llama-server.exe` |
| Communication | Codex's own application protocol | HTTP loopback to `127.0.0.1:18080` |
| Exit | Leave the Codex task | Type `/exit` to return to PowerShell |

There is no automatic message transfer from one conversation to the other. The human is the bridge: Roman decides when to ask Codex for implementation help and when to ask RAWM for a separate local response.

## Components and ownership

| Component | Responsibility |
|---|---|
| Terminal panel | Display a shell and accept keyboard input. The host application owns this. |
| PowerShell | Interpret commands and run scripts. Windows or the shell environment owns this. |
| PowerShell profile | Define `roman` when the shell starts. The user profile owns this. |
| `roman.cmd` | Provide command discovery when the profile is skipped or unavailable. |
| `Launch-RAWM.ps1` | Forward the command to the local RAWM project. |
| `Start-RAWM.ps1` | Select a compatible PowerShell runtime and import the app. |
| `app/RAWM.psm1` | Run the chat loop, route requests, call the server, and save chats. |
| `config/settings.json` | Store backend, model, limit, and interface values. |
| `context/RAWM-BEHAVIOR.md` | Supply natural-language behavior instructions to new local chats. |
| `llama-server.exe` | Run the selected model and expose a local HTTP endpoint. |
| `.gguf` model file | Supply learned model data to the inference engine. |

The contract between the host terminal and RAWM is intentionally small:

```text
When the user types roman,
start the command and show its standard input and output.
```

The host does not need to understand RAWM's model router, chat file format, or display code.

## Directory layout

```text
Rawm's local LLM/
|
+-- Start-RAWM.ps1           PowerShell entry script
+-- Register-RAWM.ps1        Profile and fallback registration
+-- Unregister-RAWM.ps1      Remove RAWM's marked registration
+-- Install-RAWM.ps1         Download runtime and model files
+-- RAWM.portable.json       Package identity and entry point
|
+-- app/
|   +-- RAWM.psm1            Main reusable PowerShell module
|
+-- config/
|   +-- settings.json        Backend, models, limits, and UI values
|
+-- context/
|   +-- RAWM-BEHAVIOR.md      Local assistant behavior text
|
+-- models/
|   +-- Qwen3.5-0.8B-Q4_K_M.gguf
|   +-- Qwen3.5-4B-Q4_K_M.gguf
|
+-- runtime/
|   +-- llama.cpp/
|       +-- llama-server.exe
|       +-- llama*.dll
|       +-- ggml*.dll
|
+-- data/
|   +-- chats/*.json          Saved conversations
|   +-- logs/*.log            Runtime diagnostics
|
+-- exports/*.md              Exported conversations
+-- tests/*.txt               Test input lines
+-- docs/                     Engineering and user documentation
```

The registration layer also creates or updates files outside the project:

```text
C:\Users\ROMAN\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
C:\Users\ROMAN\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1
C:\Users\ROMAN\AppData\Local\Microsoft\WindowsApps\roman.cmd
```

The project contains the product. The profile and command fallback provide the convenient entry point on this computer.

## File types used by the implementation

| Extension | Format | Reader or runner | RAWM use |
|---|---|---|---|
| `.ps1` | PowerShell script | PowerShell | Launcher, registration, installation |
| `.psm1` | PowerShell module | PowerShell module system | Main application logic |
| `.cmd` | Windows command script | `cmd.exe` | Fallback command shim |
| `.json` | Structured data | `ConvertFrom-Json` | Settings, manifest, saved chats |
| `.md` | Markdown text | People or a Markdown viewer | Behavior text and documentation |
| `.gguf` | Binary model format | llama.cpp runtime | Model weights and metadata |
| `.exe` | Compiled Windows program | Windows process manager | Inference server |
| `.dll` | Compiled library | The executable | Runtime dependencies |
| `.log` | Plain diagnostic text | People or log tools | Server output and errors |
| `.txt` | Plain text | PowerShell test pipeline | Automated input lines |

Do not save a PowerShell function in a `.json` file. Both files may contain readable characters, but JSON and PowerShell have different grammars and different readers.

The extension is a clue, not a translation. Renaming a `.md` file to `.ps1` does not turn documentation into a valid script.

## Command resolution

Typing `roman` only works if the shell can resolve that name. The local setup provides two paths:

```text
PowerShell starts
       |
       +--> profile loads successfully
       |        |
       |        v
       |   function global:roman exists
       |
       +--> profile does not load or function is unavailable
                |
                v
          command search finds roman.cmd
```

An engineer should inspect resolution in the actual host terminal:

```powershell
Get-Command roman -All | Format-List Name,Source,Definition
```

Possible results include a function, alias, script, or application. `-All` matters because a function and a `.cmd` file can both exist. The shell's precedence rules decide which one is used first.

The profile function is the PowerShell-native path. The `.cmd` file provides a fallback for shells that skip profiles or resolve commands through the Windows application path.

## The PowerShell profile function

**File type:** PowerShell script (`.ps1`)  
**Files:**

```text
Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

The essential code is:

```powershell
function global:roman {
    $rawmStart = 'C:\Users\ROMAN\Documents\ChatGPT\Rawm''s local LLM\Start-RAWM.ps1'
    & $rawmStart @args
}
```

| Syntax | Meaning |
|---|---|
| `function` | Define a reusable command. |
| `global:roman` | Name the function `roman` and expose it in the session's global scope. |
| `$rawmStart` | A variable containing the launcher path. |
| `&` | Execute the command or script represented by a variable. |
| `@args` | Forward arguments supplied to `roman`. |
| `Rawm''s` | Represent one apostrophe inside a single-quoted string. |

The actual registration block also searches mounted filesystem drives if the exact local path is unavailable. It looks for a folder containing both `RAWM.portable.json` and `Start-RAWM.ps1`, then verifies the expected package ID.

The two profile files are normal because Windows PowerShell and PowerShell 7 use different user profile folders. They are two entrances to the same local app, not two RAWM applications.

## The Windows command fallback

**File type:** Windows command script (`.cmd`)  
**File:** `C:\Users\ROMAN\AppData\Local\Microsoft\WindowsApps\roman.cmd`

The generated fallback is:

```cmd
@echo off
where pwsh.exe >nul 2>nul
if %errorlevel%==0 (
  pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1" %*
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ROMAN\AppData\Local\RAWM\Launch-RAWM.ps1" %*
)
```

This is not PowerShell code. It uses different syntax:

| `.cmd` item | Meaning |
|---|---|
| `@echo off` | Hide command echoing. |
| `where pwsh.exe` | Search for PowerShell 7. |
| `%errorlevel%` | Status code from the previous command. |
| `%*` | Forward every argument received by the command file. |
| `>nul 2>nul` | Hide standard output and error output from the lookup. |
| `if (...) else (...)` | Choose which PowerShell executable to run. |

The PowerShell function uses `@args`; the command script uses `%*`. They perform a similar job in two different languages.

## The project launcher: `Start-RAWM.ps1`

**File type:** PowerShell script (`.ps1`)  
**File:** project root `Start-RAWM.ps1`  
**Purpose:** Bridge the shell command to the reusable application module.

The parameter block creates a predictable command surface:

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

That enables:

```text
roman                         -> automatic routing
roman -Mode fast              -> force the small model
roman -Mode code              -> force the larger model
roman -Resume <session-id>    -> resume a saved chat
roman -NoBanner               -> suppress the opening box
```

The script stops on terminating errors:

```powershell
$ErrorActionPreference = 'Stop'
```

This makes a missing module fail immediately with a useful message rather than causing several confusing follow-up errors.

### The PowerShell 7 handoff

The local start script checks the shell version:

```powershell
if ($PSVersionTable.PSVersion.Major -lt 7) {
    $modernShell = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    $modernShellPath = if ($modernShell) { $modernShell.Source } else {
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    }

    if (-not (Test-Path -LiteralPath $modernShellPath -PathType Leaf)) {
        throw 'RAWM requires PowerShell 7. Install PowerShell 7 and run roman again.'
    }

    $forward = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $MyInvocation.MyCommand.Path,
        '-Mode', $Mode
    )

    if ($Resume) { $forward += @('-Resume', $Resume) }
    if ($New) { $forward += '-New' }
    if ($NoBanner) { $forward += '-NoBanner' }

    & $modernShellPath @forward
    return
}
```

This solves a host mismatch: the visible terminal can be Windows PowerShell 5.1 while the application runs under PowerShell 7. The child process uses the same terminal surface, so the user still sees one chat window.

`$MyInvocation.MyCommand.Path` is the current script's path. `@forward` is an argument array. The call operator `&` executes the PowerShell 7 path with those arguments.

### Finding and importing the module

```powershell
$rawmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $rawmRoot 'app\RAWM.psm1'

if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "RAWM module is missing: $modulePath"
}

Import-Module $modulePath -Force
Start-RAWMChat -Root $rawmRoot -Mode $Mode -Resume $Resume -New:$New -NoBanner:$NoBanner
```

The entry script stays small. It resolves its folder, validates the module, imports it, and calls its public entry function.

`-Force` tells PowerShell to reload the module. That is useful after a module edit because a new launch should use the saved file.

## The application module: `app/RAWM.psm1`

**File type:** PowerShell module (`.psm1`)  
**File:** `app/RAWM.psm1`  
**Purpose:** Own the chat experience and coordinate the local inference process.

The module keeps shared runtime state:

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

The `script:` scope means these values belong to the module and can be read by its functions. `$null` means “not initialized yet.” In-memory state and saved state are related but different: the module can save the session to disk so it survives after the process closes.

The module exposes one public entry point:

```powershell
Export-ModuleMember -Function Start-RAWMChat
```

The other functions are implementation helpers. This is a simple form of encapsulation: the launcher needs to know how to start RAWM, but it does not need to know every internal helper name.

### The chat loop

The central loop has this shape:

```powershell
while ($true) {
    Write-Host
    Write-RAWMColor 'roman > ' Cyan -NoNewline
    $inputText = [Console]::ReadLine()

    if ($null -eq $inputText) { break }
    if (-not $inputText.Trim()) { continue }

    if ($inputText.StartsWith('/')) {
        # handle a local RAWM command
        continue
    }

    $modelMode = Get-RAWMModelMode $inputText
    Add-RAWMMessage 'user' $inputText
    Save-RAWMSession
    $answer = Invoke-RAWMCompletion $modelMode
    Add-RAWMMessage 'assistant' $answer
    Save-RAWMSession
}
```

`while ($true)` repeats until `break`. `continue` skips to the next iteration. A slash command is handled locally; a normal sentence becomes a model request.

The complete flow is:

```text
read input
   |
   v
handle /command or normal text
   |
   v
choose fast or code
   |
   v
save user message
   |
   v
start or reuse local server
   |
   v
stream answer to screen
   |
   v
save assistant message and usage
```

## What happens when the host terminal starts RAWM

```text
Codex terminal
      |
      v
PowerShell process
      |
      +--> profile defines roman
      |          or
      +--> PATH finds roman.cmd
                 |
                 v
          Launch-RAWM.ps1
                 |
                 v
           Start-RAWM.ps1
                 |
                 v
            RAWM.psm1
                 |
                 +--> read settings
                 +--> read behavior text
                 +--> create/resume session
                 +--> wait for user input
```

The terminal host does not need a special RAWM button. It only needs to provide an interactive process that can run PowerShell and display its output.

## Model routing implementation

The routing code is deterministic and cheap. It does not send a second AI request just to classify the message.

**File type:** PowerShell module (`.psm1`)  
**File:** `app/RAWM.psm1`  
**Function:** `Get-RAWMModelMode`

```powershell
function Get-RAWMModelMode {
    param([string]$InputText)

    if ($script:Mode -in @('fast','code')) {
        return $script:Mode
    }

    $codePattern = '(?i)\b(write|implement|build|create|refactor|debug|fix|code|script|function|class|module|api|regex|powershell|python|javascript|typescript|sql|html|css|compile|stack trace|exception)\b'

    if ($InputText -match $codePattern -or $InputText -match '```') {
        return 'code'
    }

    return 'fast'
}
```

The logic is:

```text
If the user forced FAST or CODE
        |
        v
Use that forced mode

Otherwise:
        |
        v
Check for coding keywords or a fenced code block
        |
        +--> match: return code
        |
        +--> no match: return fast
```

The pattern uses regular-expression syntax:

| Pattern | Meaning |
|---|---|
| `(?i)` | Ignore uppercase/lowercase differences. |
| `\b` | Word boundary. |
| `(a|b|c)` | Match one of the alternatives. |
| `-match` | Test text against the regular expression. |
| `-in @('fast','code')` | Check whether a value is in a list. |

This is a working rule-based router, not a full language understanding system. For example, “write a birthday poem” contains `write`, so it routes to Code. The manual commands `/fast` and `/code` provide an override.

The routing commands are handled in `Invoke-RAWMCommand`:

```powershell
switch ($command) {
    '/auto' { $script:Mode = 'auto'; Write-RAWMColor 'Routing: AUTO' Green }
    '/fast' { $script:Mode = 'fast'; Write-RAWMColor 'Routing: FAST' Green }
    '/code' { $script:Mode = 'code'; Write-RAWMColor 'Routing: CODE' Green }
}
```

The labels map to model settings:

```text
auto  -> inspect the text and choose
fast  -> Qwen3.5 0.8B Q4_K_M
code  -> Qwen3.5 4B Q4_K_M
```

The words `fast` and `code` are application labels. They do not change what the underlying model was trained to do.

## Model and engine boundary

The `.gguf` model file and `llama-server.exe` have different responsibilities:

```text
Qwen3.5-0.8B-Q4_K_M.gguf
        |
        | learned numerical model data
        v
llama-server.exe
        |
        | inference calculations + HTTP endpoint
        v
http://127.0.0.1:18080
```

The PowerShell code does not implement neural-network inference. It orchestrates an existing compiled runtime and sends it a request.

The configured model files are:

| Mode | Model | Local file | Output cap |
|---|---|---|---:|
| Fast | Qwen3.5 0.8B Q4_K_M | `models/Qwen3.5-0.8B-Q4_K_M.gguf` | 384 tokens |
| Code | Qwen3.5 4B Q4_K_M | `models/Qwen3.5-4B-Q4_K_M.gguf` | 2,048 tokens |

`0.8B` and `4B` describe approximate parameter counts. `Q4_K_M` identifies a compact quantization format. The `.gguf` files are binary data and should not be edited as text.

The server lifecycle is handled by three functions:

```powershell
Test-RAWMServer
Start-RAWMServer
Stop-RAWMServer
```

`Start-RAWMServer` checks the model and executable paths, starts the process, redirects its output to `data/logs`, and polls `/health` until the server is ready. `Stop-RAWMServer` stops the process recorded in `$script:ServerProcess` when the chat exits or the selected model changes.

The local communication contract is:

```text
127.0.0.1 = this computer
18080     = local service port
/health   = readiness check
/v1/chat/completions = chat request endpoint
```

Loopback binding is deliberate. It keeps the initial implementation local to the machine instead of exposing the inference server to the network.

## Request construction

The PowerShell module creates a hashtable, then converts it to JSON:

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

This is PowerShell syntax, not JSON syntax. `@{}` creates a hashtable, `$true` is a PowerShell boolean, and `ConvertTo-Json` performs the translation.

The request uses a .NET HTTP client:

```powershell
$client = New-Object Net.Http.HttpClient
$request = New-Object Net.Http.HttpRequestMessage(
    [Net.Http.HttpMethod]::Post,
    $uri
)
$request.Content = New-Object Net.Http.StringContent(
    $body,
    [Text.Encoding]::UTF8,
    'application/json'
)
```

The actual source keeps some constructor calls on one line; this expanded version is formatted for readability. The endpoint has a familiar chat-completions shape, but the configured URL points to the local engine.

## Streaming output

The request sets `stream = $true`, so the server sends pieces instead of waiting for one complete response. RAWM reads the response incrementally:

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
}
```

The loop reads one line, ignores lines that are not data events, removes the `data:` prefix, stops at `[DONE]`, and converts each JSON event into a PowerShell object.

When a content piece exists, the module has two destinations:

```powershell
$safe = Remove-RAWMControlSequence ([string]$piece)
[void]$builder.Append($safe)
Write-RAWMWrappedText -Text $safe -State $wrapState
```

```text
safe content
    |
    +--> StringBuilder: complete answer for save/copy/export
    |
    +--> wrapper: readable display in the terminal
```

This separation avoids using visible console formatting as the saved answer's source of truth.

The request cleanup uses `finally`:

```powershell
finally {
    if ($reader) { $reader.Dispose() }
    if ($stream) { $stream.Dispose() }
    if ($response) { $response.Dispose() }
    $request.Dispose()
    $client.Dispose()
}
```

The cleanup runs after success or failure. `Dispose()` releases network and stream resources.

## Word wrapping in a host terminal

The bottom terminal panel can be narrower than a full-screen PowerShell window. A terminal application must measure the current console width rather than assume a fixed number of columns.

**File type:** PowerShell module (`.psm1`)  
**File:** `app/RAWM.psm1`  
**Functions:** `Get-RAWMTextWidth`, `Write-RAWMWrappedText`

The width helper is:

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

The default is 80. If the console reports a usable width, the function uses it and leaves one column of margin. The `try/catch` protects hosts where the width cannot be read normally.

The wrapper receives state:

```powershell
$wrapState = @{ Pending = ''; Column = 0 }
```

`Pending` holds unfinished display text. `Column` records the current visible column.

An incoming network piece may end in `str` while the next begins with `eaming`. The wrapper buffers incomplete non-space text so it can avoid breaking every network event at an arbitrary place.

For normal words, the wrapper starts a new line when the next word would exceed the width. For a long unbroken string, it prints chunks using `Substring`. This handles URLs, identifiers, and generated code lines that have no convenient spaces.

The final response flushes pending text:

```powershell
Write-RAWMWrappedText -Text '' -State $wrapState -Flush
Write-Host
```

The `-Flush` switch means no more response pieces are coming. Without it, a final word with no following whitespace might remain buffered.

The screen formatting does not rewrite the saved response. The accumulator receives the original safe response; the wrapper controls only how that response is displayed.

The current implementation handles ordinary character-width text well. It does not redraw old console history after the panel is resized, and unusual wide Unicode glyphs or emoji may not occupy exactly one character column.

## Settings and behavior context

### `config/settings.json`

**File type:** JSON data (`.json`)  
**Purpose:** Store values that the module reads at runtime.

The backend and model configuration have this shape:

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 18080,
    "contextSize": 4096
  },
  "models": {
    "fast": {
      "file": "models/Qwen3.5-0.8B-Q4_K_M.gguf",
      "maxTokens": 384
    }
  }
}
```

JSON requires double-quoted names, colons between names and values, commas between entries, and matching braces. JSON uses `true` and `false`; it does not use PowerShell's `$true` and `$false`.

The module reads the file as an object:

```powershell
Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
```

Then it can access values such as:

```powershell
$script:Settings.backend.port
$script:Settings.models.fast.file
```

A setting has no effect unless code reads it. Adding a property to JSON alone does not implement a feature.

### `context/RAWM-BEHAVIOR.md`

**File type:** Markdown (`.md`)  
**Purpose:** Natural-language context sent to the local model when a new chat is created.

The module reads the file:

```powershell
$behavior = Get-Content -LiteralPath (
    Join-Path $script:Root 'context\RAWM-BEHAVIOR.md'
) -Raw -Encoding UTF8
```

Then it creates a system message:

```powershell
[pscustomobject]@{
    role = 'system'
    content = $behavior
}
```

The Markdown file is not executable. It matters because the module consumes its text and includes it in the model request.

## Session state and local conversation files

**File type:** JSON (`.json`)  
**Folder:** `data/chats/`

`New-RAWMSession` creates a session object with an identifier, timestamps, messages, and usage totals:

```powershell
$now = Get-Date
$id = $now.ToString('yyyyMMdd-HHmmss') + '-' +
    ([guid]::NewGuid().ToString('N').Substring(0, 6))

$script:Session = [pscustomobject]@{
    schemaVersion = 1
    id = $id
    title = 'New chat'
    createdAt = $now.ToString('o')
    updatedAt = $now.ToString('o')
    messages = [System.Collections.ArrayList]@()
    totals = [pscustomobject]@{
        promptTokens = 0
        completionTokens = 0
        turns = 0
    }
}
```

The timestamp makes files sort naturally. The short GUID suffix reduces the chance of duplicate names when two sessions start in the same second.

The save routine writes a temporary file and moves it into place:

```powershell
$path = Join-Path $folder ($script:Session.id + '.json')
$temp = "$path.tmp"
$json = $script:Session | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText($temp, $json, (New-Object Text.UTF8Encoding($false)))
Move-Item -LiteralPath $temp -Destination $path -Force
```

This reduces the chance of leaving the final JSON file partially written if the process stops during the write. It is not a complete backup system.

The saved conversation is separate from the host application's conversation. Codex cannot automatically see RAWM's messages simply because both are visible in the same window. A future bridge would need to explicitly read a chat file or call a RAWM API.

## Slash commands

Inside RAWM, a line beginning with `/` is handled locally instead of being sent to a model.

The parser separates the command and optional argument:

```powershell
$parts = $InputText.Trim().Split(
    @(' '),
    2,
    [StringSplitOptions]::RemoveEmptyEntries
)
$command = $parts[0].ToLowerInvariant()
$argument = if ($parts.Count -gt 1) { $parts[1] } else { '' }
```

The current commands include:

```text
/help       show commands
/new        create a new session
/resume     load the newest saved session
/auto       restore automatic routing
/fast       force the smaller model
/code       force the larger model
/model      show model file status
/usage      show local usage counts
/paste      enter multiline input
/copy       copy the last answer
/copy code  copy the first fenced code block
/export     save the conversation as Markdown
/stop       stop the local server
/exit       save and return to PowerShell
```

The command handler uses a `switch`:

```powershell
switch ($command) {
    '/help'   { Show-RAWMHelp }
    '/new'    { New-RAWMSession }
    '/auto'   { $script:Mode = 'auto' }
    '/fast'   { $script:Mode = 'fast' }
    '/code'   { $script:Mode = 'code' }
    '/export' { $path = Export-RAWMSession }
    '/exit'   {
        return [pscustomobject]@{
            Handled = $true
            Exit = $true
        }
    }
    default {
        Write-RAWMColor "Unknown command: $command. Use /help." Amber
    }
}
```

The `/exit` branch returns an object with an `Exit` property. The outer loop checks that property and breaks. The inner function communicates a decision to the outer loop without directly owning the whole application.

## Reproduction procedure

This is the implementation sequence for another engineer on a compatible Windows computer.

### 1. Put the project in a known root

Use one project folder containing the start script, module, configuration, runtime, models, and data folders. Resolve paths from the start script rather than assuming a drive letter.

```powershell
$rawmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
```

### 2. Install the runtime and model files

The existing installer accepts a component:

```powershell
.\Install-RAWM.ps1 -Component runtime
.\Install-RAWM.ps1 -Component fast
.\Install-RAWM.ps1 -Component code
.\Install-RAWM.ps1 -Component all
```

The installer downloads a llama.cpp Windows runtime and the two configured GGUF files. A production implementation should pin and verify release assets and model checksums before treating installation as complete.

### 3. Register the command

```powershell
.\Register-RAWM.ps1 -AllPowerShellEditions
```

The script adds a marked `roman` function to both user profile paths and creates the fallback launcher files. It backs up existing profiles before writing.

The two profile locations are:

```text
Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

Two profiles are normal because Windows PowerShell and PowerShell 7 are separate editions. The registration targets both so the same command is available whichever edition the host terminal starts.

### 4. Allow the local script to load

If the local Windows user has a restrictive setting, use the narrow user-scope policy intended for locally created scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

The engineer should inspect policy before changing it:

```powershell
Get-ExecutionPolicy -List
```

An organization-managed policy may take precedence. Execution policy is a script-loading control, not complete application security.

### 5. Open the host terminal

In Codex or another supported host, open its terminal panel. Verify that the terminal uses the intended user and shell:

```powershell
$PSVersionTable.PSVersion
$env:USERNAME
$PROFILE
Get-Location
```

The host must be able to run PowerShell and display standard input/output. It does not need to know RAWM's internal functions.

### 6. Verify command resolution

```powershell
Get-Command roman -All | Format-List Name,Source,Definition
```

The result should point to the registered function, the local `.cmd` fallback, or both. If neither appears, the problem is at the host/shell registration layer, before RAWM itself starts.

### 7. Launch the app

```powershell
roman
```

Expected output resembles:

```text
RAWM
LOCAL | Private | Type /help for commands
Routing: AUTO | Session: <session-id>

roman >
```

### 8. Send one Fast and one Code request

```text
roman > Say hello in one short sentence.
roman > Write a short PowerShell function named Get-Greeting.
```

The first normally routes to Fast. The second normally routes to Code because of coding keywords.

### 9. Exit cleanly

```text
roman > /exit
```

Expected result: the session is saved, the app-owned server process stops, and the PowerShell prompt returns.

## Exact commands used on Roman's computer

These are the operational commands used during the local repair and verification. They are included as a reproducible history, not as instructions to rerun against the already working installation.

### Inspect the profile

```powershell
Get-Content -LiteralPath 'C:\Users\ROMAN\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1'
```

### List the project

```powershell
Get-ChildItem -Force
rg --files -g AGENTS.md -g '*.ps1' -g '*.psm1' -g '*.json' -g '*.md' -g '*.txt'
```

### Inspect the command

```powershell
Get-Command roman -All | Format-List Name,Source,Definition
```

### Register both editions

```powershell
.\Register-RAWM.ps1 -AllPowerShellEditions
```

### Set the current-user execution policy

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

### Install components

```powershell
.\Install-RAWM.ps1 -Component fast
.\Install-RAWM.ps1 -Component all
```

### Verify the real shell

```powershell
powershell.exe -Command "Get-ExecutionPolicy -List"
powershell.exe -Command "Get-Command roman -All"
```

### Test the normal command path

```powershell
Get-Content tests\smoke-input.txt | powershell.exe -Command roman
```

The smoke file contained a short request followed by `/exit`. A successful run showed the RAWM banner, a real Fast response, usage information, and the closing message.

### Test the direct start path

```powershell
Get-Content tests\code-smoke-input.txt |
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-RAWM.ps1
```

This bypassed profile loading and tested the start script directly. It produced a short `Get-Greeting` function using Code mode.

### Inspect the server process and logs

```powershell
Get-Process powershell,pwsh,llama-server -ErrorAction SilentlyContinue |
    Select-Object Id,CPU,WorkingSet,StartTime

Get-Content data\logs\llama-server.err.log -Tail 12
```

The process inspection is useful for distinguishing “the app never started” from “the model server started but is still loading.”

## Test matrix for the host-terminal experience

| Test | Host | Shell | Expected result |
|---|---|---|---|
| Direct start | Ordinary terminal | PowerShell 7 | RAWM starts and accepts input. |
| Direct start | Ordinary terminal | Windows PowerShell | Launcher forwards to PowerShell 7 when available. |
| Named command | Host terminal panel | PowerShell | `Get-Command roman` resolves. |
| Fast response | Host terminal panel | PowerShell | Fast model answers and output wraps. |
| Code response | Host terminal panel | PowerShell | Code model answers and output wraps. |
| Exit | Host terminal panel | PowerShell | RAWM saves and returns to the shell prompt. |
| No profile | Any terminal | `-NoProfile` | Fallback command works if discoverable. |
| Narrow panel | Host terminal panel | PowerShell | New streamed lines fit visible width. |
| Missing model | Any terminal | PowerShell | Clear expected-path error. |
| Missing runtime | Any terminal | PowerShell | Clear runtime-path error. |

The host-terminal test validates the discovery Roman noticed. A direct script test proves the app works; it does not prove the host can resolve `roman`.

## Failure modes and diagnosis

### `roman` is not recognized

Run these in the exact terminal where the failure occurred:

```powershell
Get-Command roman -All
$PROFILE
$PSVersionTable.PSVersion
Get-Location
```

Possible causes:

- the host started PowerShell with `-NoProfile`;
- the relevant profile was never registered;
- the profile has a parser error and failed before defining `roman`;
- the directory containing `roman.cmd` is not on `PATH`;
- the terminal uses a different Windows user;
- the host is running a shell other than PowerShell.

The important diagnosis is whether the failure occurs before RAWM starts. If `Get-Command roman` finds nothing, inspect shell registration first. There is no point debugging the model server until the command can launch the app.

### Parser errors appear before the prompt

Read the first error and inspect the profile. Common causes include an unclosed quote, unmatched brace, malformed pipeline, or code-generation replacement that interpreted `$` variables.

The number of profile files is not itself the problem. Windows PowerShell and PowerShell 7 can use different user profile paths. The applicable profile must contain valid code.

### Scripts are disabled

Run:

```powershell
Get-ExecutionPolicy -List
```

An enforced machine or user policy may take precedence. `RemoteSigned` for the current user was the local repair setting. A host that launches a child with `-ExecutionPolicy Bypass` is making a separate per-process choice.

### RAWM opens but the model fails

Check the expected files:

```powershell
Test-Path -LiteralPath '.\app\RAWM.psm1' -PathType Leaf
Test-Path -LiteralPath '.\runtime\llama.cpp\llama-server.exe' -PathType Leaf
Test-Path -LiteralPath '.\models\Qwen3.5-0.8B-Q4_K_M.gguf' -PathType Leaf
Test-Path -LiteralPath '.\models\Qwen3.5-4B-Q4_K_M.gguf' -PathType Leaf
```

Then inspect:

```powershell
Get-Content data\logs\llama-server.out.log -Tail 12
Get-Content data\logs\llama-server.err.log -Tail 12
```

The runtime may fail because of missing DLLs, architecture mismatch, insufficient memory, an occupied port, or a model format mismatch.

### RAWM opens but output goes past the terminal edge

Confirm the running source contains the wrapper functions:

```powershell
rg -n 'Get-RAWMTextWidth|Write-RAWMWrappedText' app\RAWM.psm1
```

Then exit and relaunch RAWM so PowerShell imports the current module. A process that already loaded an older module can continue using the old in-memory definitions.

### RAWM and Codex appear to share files

They share the computer and may share the current working directory. A file created by one may be visible to the other because both can access the filesystem. That is filesystem co-location, not conversation synchronization.

### The terminal closes when RAWM exits

That is usually a host behavior, not an AI behavior. A terminal host can choose whether a command process runs in a persistent panel, a new tab, or a disposable shell. The RAWM application can save and return to its parent shell, but it cannot force every host to keep a panel open.

## What a true Codex integration would mean

The screenshot shows host-level integration through a terminal surface. A deeper integration would require a separate contract:

| Desired behavior | Integration shape |
|---|---|
| Run RAWM beside Codex | Terminal hosting; the current approach. |
| Let Codex call RAWM as a named tool | MCP server or another supported tool protocol. |
| Display RAWM as a custom panel | Host-specific UI extension or supported app/widget surface. |
| Share structured messages | Explicit IPC, local HTTP API, or file protocol. |
| Let Codex inspect or edit RAWM | Workspace filesystem and terminal access. |
| Keep inference local | RAWM continues using `llama-server.exe` and loopback. |

Do not call the current design an MCP integration unless an MCP server was actually built and registered. Do not claim that Codex can see RAWM's messages unless an explicit bridge transfers them.

A future bridge might expose operations like:

```text
rawm.status
rawm.ask
rawm.list_sessions
rawm.resume_session
```

That would change the architecture. The terminal workflow is valuable because it has a small host contract: start the command and display the terminal.

## Code ownership and process boundaries

The host application owns the terminal panel. The PowerShell process owns the `roman` command and the RAWM child process. RAWM owns the `llama-server.exe` process it starts.

```text
Codex process
      |
      +--> terminal host process
                 |
                 +--> PowerShell process
                            |
                            +--> RAWM PowerShell module
                            |
                            +--> llama-server.exe
```

The exact parent-process tree can vary by host. The conceptual ownership matters more than a specific process ID:

- the host creates or hosts the terminal;
- PowerShell interprets the command;
- RAWM manages its chat and server lifecycle;
- the server loads the model and answers through localhost.

If the host terminates the terminal process, RAWM may not reach its normal `finally` cleanup. A robust implementation should save often, as RAWM does after adding messages and after receiving answers.

## Security notes for an engineer

The word `roman` is a convenient command name, not a password. Anyone with access to the same user account and command path can launch it.

The server binds to `127.0.0.1` in this design. That limits the initial service to the same computer. A future remote mode should require deliberate network binding, authentication, authorization, and testing.

The profile and launcher can execute local scripts. They should be treated as code with the user's permissions. Use clear markers, backups, validation, and narrow path handling when writing profile registration code.

Saved chats are ordinary local JSON files. They may contain personal messages or generated code. The current RAWM application does not encrypt them. Document this before sharing the project or copying the `data` folder to another machine.

Model output is text until a person or another controlled system chooses to execute it. RAWM displays generated PowerShell but does not automatically run generated code. A future execution feature would need a separate approval and isolation design.

## How to read the implementation as an engineer

Trace a visible action through the call graph.

For `/copy code`:

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

For automatic routing:

```text
normal user message
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

For model settings:

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
max_tokens and temperature in request JSON
```

Ask five questions while reading a function:

1. What inputs does `param(...)` define?
2. What values does it read?
3. What values or side effects does it produce?
4. Which other functions does it call?
5. What happens if an expected file, process, or response is missing?

This is data-flow tracing. You follow the value from the user's action to the visible result.

## Syntax that matters in this integration

### PowerShell variables and paths

```powershell
$rawmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $rawmRoot 'app\RAWM.psm1'
```

`$name` refers to a variable. `=` assigns a value. `Split-Path` obtains a parent folder. `Join-Path` combines path pieces.

### Single quotes and apostrophes

```powershell
$folderName = 'Rawm''s local LLM'
```

The result is `Rawm's local LLM`. Two adjacent single quotes represent one apostrophe inside a single-quoted string.

### Double quotes and interpolation

```powershell
$uri = "http://$($host):$($port)/health"
```

PowerShell evaluates the expressions inside `$()` and inserts their results into the double-quoted string.

### Arrays and hashtables

```powershell
$modes = @('fast', 'code')
$options = @{ Mode = 'fast'; MaxTokens = 384 }
```

`@(...)` creates a list. `@{...}` creates named values. The request body uses a hashtable before converting it to JSON.

### Pipes

```powershell
Get-Content settings.json -Raw | ConvertFrom-Json
```

The output of the first command becomes input to the second. An empty pipe element, such as a trailing `|`, is a parser error.

### Braces and code blocks

```powershell
if ($ready) {
    Write-Host 'Server is ready'
}
```

Matching braces tell the parser which commands belong to the condition. Matching quotes tell it where text begins and ends.

### `.cmd` variables are different

```cmd
%errorlevel%
%*
```

These are command-shell variables. They are not PowerShell variables. PowerShell's equivalent argument forwarding expression is `@args`.

### JSON syntax is different again

```json
{
  "port": 18080,
  "enabled": true
}
```

This is valid JSON. It uses double-quoted property names and JSON boolean syntax. It is not a PowerShell hashtable.

## Engineer handoff checklist

```text
[ ] Confirm the host provides an interactive terminal.
[ ] Confirm the terminal runs under the intended Windows user.
[ ] Confirm the shell and PowerShell edition it starts.
[ ] Confirm the RAWM project root is present.
[ ] Confirm llama-server.exe and its DLLs exist.
[ ] Confirm both expected .gguf model files exist.
[ ] Confirm settings.json points to the local filenames.
[ ] Confirm RAWM-BEHAVIOR.md exists.
[ ] Register the applicable PowerShell profiles if desired.
[ ] Confirm roman.cmd is discoverable when profiles are skipped.
[ ] Run Get-Command roman -All.
[ ] Run one Fast response test.
[ ] Run one Code response test.
[ ] Test /exit and return to the shell.
[ ] Test a narrow terminal panel for wrapping.
[ ] Record whether the host uses a persistent terminal process.
[ ] State clearly whether this is terminal co-location or a true app integration.
```

## Short technical summary

To reproduce this workflow, build a terminal application with a PowerShell launcher, register a shell command named `roman`, start a local llama.cpp server with a selected GGUF model, send chat requests to a loopback HTTP endpoint, stream and wrap the response, and save sessions locally.

To make it work inside Codex, provide a Codex terminal surface to the user. No direct modification of Codex is required for the side-by-side experience shown in the screenshot. The visible effect is produced by a clear chain of contracts:

```text
host terminal
    |
    v
PowerShell command resolution
    |
    v
RAWM launcher
    |
    v
RAWM chat module
    |
    v
local inference server
    |
    v
local model response
```

The short command is the memorable part. The engineering is the chain underneath it: host to terminal, terminal to shell, shell to launcher, launcher to module, module to server, and server to model.
