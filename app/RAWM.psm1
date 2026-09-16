Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$script:Ansi = @{
    Reset = "`e[0m"; Cyan = "`e[96m"; Gray = "`e[90m"; Green = "`e[92m"
    Amber = "`e[93m"; Red = "`e[91m"; White = "`e[97m"
}
$script:Root = $null
$script:Settings = $null
$script:Session = $null
$script:Mode = 'auto'
$script:ActiveModelMode = $null
$script:ServerProcess = $null
$script:LastAnswer = ''
$script:LastUsage = $null
. (Join-Path $PSScriptRoot 'RAWMDebug.ps1')
. (Join-Path $PSScriptRoot 'RAWMModels.ps1')
. (Join-Path $PSScriptRoot 'RAWMAgent.ps1')
. (Join-Path $PSScriptRoot 'RAWMRuntime.ps1')
. (Join-Path $PSScriptRoot 'RAWMBrowser.ps1')
. (Join-Path $PSScriptRoot 'RAWMCodeDraft.ps1')
. (Join-Path $PSScriptRoot 'RAWMFiles.ps1')

function Get-RAWMTextWidth {
    $visibleWidth = 80
    try {
        if ([Console]::WindowWidth -gt 0) { $visibleWidth = [Console]::WindowWidth }
    } catch {}
    return [Math]::Max(1, $visibleWidth - 1)
}

function Write-RAWMWrappedText {
    param([string]$Text, [hashtable]$State, [switch]$Flush, [string]$Color='White')
    # Buffer only the unfinished word, so streaming still appears as it arrives.
    $State.Pending += $Text.Replace("`r", '').Replace("`t", '    ')
    while ($State.Pending.Length -gt 0) {
        $width = Get-RAWMTextWidth
        $match = [regex]::Match($State.Pending, '^(\n|[^\S\n]+|[^\s]+)')
        $token = $match.Value
        if (-not $Flush -and $token -notmatch '\s' -and $token.Length -eq $State.Pending.Length -and $token.Length -lt $width) { break }
        $State.Pending = $State.Pending.Substring($token.Length)
        if ($token -eq "`n") {
            Write-Host
            $State.Column = 0
            continue
        }
        if ($token -notmatch '^\s+$' -and $State.Column -gt 0 -and ($State.Column + $token.Length) -gt $width) {
            Write-Host
            $State.Column = 0
        }
        while ($token.Length -gt 0) {
            $available = $width - $State.Column
            if ($available -le 0) {
                Write-Host
                $State.Column = 0
                $available = $width
                if ($token -match '^ +$') { break }
            }
            $count = [Math]::Min($available, $token.Length)
            Write-Host $token.Substring(0, $count) -NoNewline -ForegroundColor $Color
            $State.Column += $count
            $token = $token.Substring($count)
        }
    }
}

function Write-RAWMColor {
    param([string]$Text, [string]$Color = 'White', [switch]$NoNewline)
    $nativeColor=if ($Color -eq 'Amber') {'Yellow'} else {$Color}
    if ($NoNewline) { Write-Host $Text -ForegroundColor $nativeColor -NoNewline }
    else {
        Write-RAWMWrappedText -Text $Text -State @{ Pending=''; Column=0 } -Flush -Color $nativeColor
        Write-Host
    }
}

function Remove-RAWMControlSequence {
    param([AllowEmptyString()][string]$Text)
    if ($null -eq $Text) { return '' }
    return [regex]::Replace($Text, '\x1B\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '')
}

function Get-RAWMPasscode {
    $passcode = 'roman'
    if ($script:Settings -and $script:Settings.PSObject.Properties['interface'] -and
        $script:Settings.interface -and $script:Settings.interface.PSObject.Properties['passcode']) {
        $candidate = [string]$script:Settings.interface.passcode
        if (-not [string]::IsNullOrWhiteSpace($candidate)) { $passcode = $candidate.Trim() }
    }
    return Remove-RAWMControlSequence $passcode
}

function Set-RAWMPasscode {
    param([string]$Name)
    $candidate=$Name.Trim()
    if ($candidate -notmatch '^[\p{L}\p{N}][\p{L}\p{N} _-]{0,31}$') {
        throw 'Use 1-32 letters, numbers, spaces, underscores or hyphens, starting with a letter or number.'
    }
    $path=Join-Path $script:Root 'config/settings.local.json'
    Assert-RAWMNoLinks $path
    $updated=if (Test-Path -LiteralPath $path) { Read-RAWMJson $path } else { $script:Settings|ConvertTo-Json -Depth 30|ConvertFrom-Json }
    if (-not $updated.PSObject.Properties['interface'] -or -not $updated.interface) {
        $updated|Add-Member -NotePropertyName interface -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $updated.interface|Add-Member -NotePropertyName passcode -NotePropertyValue $candidate -Force
    $temp=$path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($temp,($updated|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temp -Destination $path -Force
    } finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
    if (-not $script:Settings.PSObject.Properties['interface'] -or -not $script:Settings.interface) {
        $script:Settings|Add-Member -NotePropertyName interface -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $script:Settings.interface|Add-Member -NotePropertyName passcode -NotePropertyValue $candidate -Force
}

function Write-RAWMBox {
    param([string]$Title, [string[]]$Lines, [string]$Color = 'Cyan')
    $width = [Math]::Max(1, [Math]::Min(62, (Get-RAWMTextWidth) - 4))
    $unicode = [bool]$script:Settings.interface.unicodeBorders
    if ($unicode) {
        $tl=[string][char]0x256D; $tr=[string][char]0x256E
        $bl=[string][char]0x2570; $br=[string][char]0x256F
        $h=[string][char]0x2500; $v=[string][char]0x2502
    }
    else { $tl='+'; $tr='+'; $bl='+'; $br='+'; $h='-'; $v='|' }
    $safeTitle = Remove-RAWMControlSequence $Title
    $topLabel = if ($safeTitle) { " $safeTitle " } else { '' }
    $remaining = [Math]::Max(0, $width - $topLabel.Length)
    Write-RAWMColor ($tl + $topLabel + ($h * $remaining) + $tr) $Color
    foreach ($line in $Lines) {
        $clean = Remove-RAWMControlSequence $line
        while ($clean.Length -gt $width) {
            Write-RAWMColor ($v + ' ' + $clean.Substring(0, $width) + ' ' + $v) $Color
            $clean = $clean.Substring($width)
        }
        Write-RAWMColor ($v + ' ' + $clean.PadRight($width) + ' ' + $v) $Color
    }
    Write-RAWMColor ($bl + ($h * ($width + 2)) + $br) $Color
}

function Read-RAWMJson {
    param([string]$Path)
    Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Save-RAWMSession {
    if (-not $script:Session) { return }
    $folder = Join-Path $script:Root 'data\chats'
    if (-not (Test-Path -LiteralPath $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
    $path = Join-Path $folder ($script:Session.id + '.json')
    $temp = "$path.tmp"
    $json = $script:Session | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($temp, $json, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $temp -Destination $path -Force
}

function New-RAWMSession {
    $now = Get-Date
    $id = $now.ToString('yyyyMMdd-HHmmss') + '-' + ([guid]::NewGuid().ToString('N').Substring(0, 6))
    $behavior = Get-Content -LiteralPath (Join-Path $script:Root 'context\RAWM-BEHAVIOR.md') -Raw -Encoding UTF8
    $script:Session = [pscustomobject]@{
        schemaVersion = 1; id = $id; title = 'New chat'; createdAt = $now.ToString('o')
        updatedAt = $now.ToString('o'); messages = [System.Collections.ArrayList]@(
            [pscustomobject]@{ role = 'system'; content = $behavior }
        ); totals = [pscustomobject]@{ promptTokens = 0; completionTokens = 0; turns = 0 }
    }
    Save-RAWMSession
}

function Resume-RAWMSession {
    param([string]$Id)
    $folder = Join-Path $script:Root 'data\chats'
    if (-not (Test-Path -LiteralPath $folder)) { throw 'No saved chats exist yet.' }
    if ($Id) { $path = Join-Path $folder ($Id + '.json') }
    else { $path = Get-ChildItem -LiteralPath $folder -Filter '*.json' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName }
    if (-not $path -or -not (Test-Path -LiteralPath $path)) { throw "Saved chat was not found: $Id" }
    $loaded = Read-RAWMJson $path
    $loaded.messages = [System.Collections.ArrayList]@($loaded.messages)
    $script:Session = $loaded
}

function Get-RAWMModelMode {
    param([string]$InputText)
    if ($script:Mode -in @('fast','code')) { return $script:Mode }
    $codePattern = '(?i)\b(write|implement|build|create|refactor|debug|fix|code|script|function|class|module|api|regex|powershell|python|javascript|typescript|sql|html|css|compile|stack trace|exception)\b'
    if ($InputText -match $codePattern -or $InputText -match '```') { return 'code' }
    return 'fast'
}

function Get-RAWMModelConfig {
    param([ValidateSet('fast','code')][string]$ModelMode)
    $entry = $script:Settings.models.$ModelMode
    if ($script:Settings.backend.type -eq 'ollama') {
        return [pscustomobject]@{ Mode=$ModelMode; Name=[string]$entry.name; Path=''; MaxTokens=[int]$entry.maxTokens; Temperature=[double]$entry.temperature }
    }
    $path = if ([IO.Path]::IsPathRooted([string]$entry.file)) { [string]$entry.file } else { Join-Path $script:Root ([string]$entry.file) }
    [pscustomobject]@{ Mode=$ModelMode; Name=[string]$entry.name; Path=$path; MaxTokens=[int]$entry.maxTokens; Temperature=[double]$entry.temperature }
}

function Test-RAWMServer {
    try {
        if ($script:Settings.backend.type -eq 'ollama') {
            $null = Invoke-RestMethod -Uri ((Get-RAWMBackendUrl) + '/api/tags') -TimeoutSec 2 -NoProxy -MaximumRedirection 0
            return $true
        }
        $uri = (Get-RAWMBackendUrl) + '/health'
        $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 2 -NoProxy -MaximumRedirection 0
        return ($response.status -in @('ok','no slot available'))
    } catch { return $false }
}

function Stop-RAWMServer {
    if ($script:ServerProcess -and -not $script:ServerProcess.HasExited) {
        Stop-Process -Id $script:ServerProcess.Id -Force -ErrorAction SilentlyContinue
        $script:ServerProcess.WaitForExit(3000) | Out-Null
    }
    $script:ServerProcess = $null
    $script:ActiveModelMode = $null
}

function Start-RAWMServer {
    param([ValidateSet('fast','code')][string]$ModelMode)
    Assert-RAWMLocalBackend
    if ($script:Settings.backend.type -eq 'ollama') {
        $model = Get-RAWMModelConfig $ModelMode
        try { $installed = Invoke-RestMethod -Uri ((Get-RAWMBackendUrl) + '/api/tags') -TimeoutSec 5 -NoProxy -MaximumRedirection 0 }
        catch { throw 'Ollama is unavailable. Start the Ollama application and try again.' }
        if ($model.Name -cnotin @($installed.models | ForEach-Object { $_.name })) {
            throw "Ollama model '$($model.Name)' is not installed. Check ollama list and config/settings.local.json."
        }
        $script:ActiveModelMode = $ModelMode
        return
    }
    if ($script:ActiveModelMode -eq $ModelMode -and (Test-RAWMServer)) { return }
    Stop-RAWMServer
    # Prefer the configured port; an existing session must not prevent this one from starting.
    $bindAddress = if ($script:Settings.backend.host -eq '::1') { [Net.IPAddress]::IPv6Loopback } else { [Net.IPAddress]::Loopback }
    $probe = [Net.Sockets.TcpListener]::new($bindAddress, [int]$script:Settings.backend.port)
    $probe.ExclusiveAddressUse = $true
    try {
        try { $probe.Start() }
        catch {
            $probe.Stop()
            $probe = [Net.Sockets.TcpListener]::new($bindAddress, 0)
            $probe.ExclusiveAddressUse = $true
            $probe.Start()
        }
        # Session-local only: all health, chat, planning, and inspection requests use this port.
        $script:Settings.backend.port = $probe.LocalEndpoint.Port
    }
    finally { $probe.Stop() }
    $model = Get-RAWMModelConfig $ModelMode
    if (-not (Test-Path -LiteralPath $model.Path -PathType Leaf)) {
        throw "The $ModelMode model is not installed. Run .\Install-RAWM.ps1, or use /model after installing a model.`nExpected: $($model.Path)"
    }
    $server = Join-Path $script:Root 'runtime\llama.cpp\llama-server.exe'
    if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
        throw "The local inference runtime is not installed. Run .\Install-RAWM.ps1.`nExpected: $server"
    }
    $logFolder = Join-Path $script:Root 'data\logs'
    New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
    $logName = 'llama-server-' + $PID + '-' + $script:Settings.backend.port
    $stdout = Join-Path $logFolder ($logName + '.out.log')
    $stderr = Join-Path $logFolder ($logName + '.err.log')
    $quotedModelPath = '"' + $model.Path.Replace('"', '\"') + '"'
    $args = @('-m', $quotedModelPath, '--host', [string]$script:Settings.backend.host, '--port', [string]$script:Settings.backend.port,
        '-c', [string]$script:Settings.backend.contextSize, '-ngl', [string]$script:Settings.backend.gpuLayers, '--jinja')
    Write-RAWMColor "Loading $($model.Name)..." Amber
    $script:ServerProcess = Start-Process -FilePath $server -ArgumentList $args -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $operation=New-RAWMOperation "Loading $($model.Name)" ([int]$script:Settings.backend.startupTimeoutSeconds)
    try {
    while ($true) {
        Update-RAWMOperation $operation
        if ($script:ServerProcess.HasExited) {
            $detail = if (Test-Path $stderr) { (Get-Content -LiteralPath $stderr -Tail 12) -join "`n" } else { 'No server log was produced.' }
            throw "llama-server stopped during startup.`n$detail"
        }
        if (Test-RAWMServer) { $script:ActiveModelMode = $ModelMode; return }
        Start-Sleep -Milliseconds 300
    }
    } catch { Stop-RAWMServer; throw }
    finally { Close-RAWMOperation $operation }
}

function Add-RAWMMessage {
    param([string]$Role, [string]$Content)
    [void]$script:Session.messages.Add([pscustomobject]@{ role=$Role; content=$Content })
    $script:Session.updatedAt = (Get-Date).ToString('o')
    if ($Role -eq 'user' -and $script:Session.title -eq 'New chat') {
        $script:Session.title = if ($Content.Length -gt 48) { $Content.Substring(0,48) } else { $Content }
    }
}

function Invoke-RAWMCompletion {
    param([ValidateSet('fast','code')][string]$ModelMode, [string]$SystemInstruction)
    Start-RAWMServer $ModelMode
    $model = Get-RAWMModelConfig $ModelMode
    $uri = (Get-RAWMBackendUrl) + '/v1/chat/completions'
    $payload = @{
        model = $model.Name; messages = @(Get-RAWMChatMessages -SystemInstruction $SystemInstruction); stream = $true
        stream_options = @{ include_usage = $true }; max_tokens = $model.MaxTokens
        temperature = $model.Temperature; chat_template_kwargs = @{ enable_thinking = $false }
    }
    $native = $script:Settings.backend.type -eq 'ollama'
    if ($native) {
        $uri = (Get-RAWMBackendUrl) + '/api/chat'
        $options=@{num_predict=$model.MaxTokens; temperature=$model.Temperature; num_ctx=[int]$script:Settings.backend.contextSize}
        $entry=$script:Settings.models.$ModelMode
        if ($entry.PSObject.Properties['numGpu']) { $options.num_gpu=[int]$entry.numGpu }
        $payload=@{model=$model.Name; messages=$payload.messages; stream=$true; think=$false; keep_alive='10m'; options=$options}
    }
    $body=$payload | ConvertTo-Json -Depth 12 -Compress
    Write-RAWMDebug 'request.started' @{model=$model.Name; route=$ModelMode; transport=$(if ($native) {'ollama'} else {'openai-compatible'}); messages=$payload.messages.Count}
    $client = [Net.Http.HttpClient]::new([Net.Http.HttpClientHandler]@{UseProxy=$false;AllowAutoRedirect=$false})
    # The operation timer below owns cancellation; HttpClient's default is only 100s.
    $client.Timeout = [Threading.Timeout]::InfiniteTimeSpan
    $request = New-Object Net.Http.HttpRequestMessage([Net.Http.HttpMethod]::Post, $uri)
    $request.Content = New-Object Net.Http.StringContent($body, [Text.Encoding]::UTF8, 'application/json')
    $started = Get-Date
    $firstToken = $null
    $builder = New-Object Text.StringBuilder
    $wrapState = @{ Pending=''; Column=0 }
    $usage = $null
    $response = $null
    $stream = $null
    $reader = $null
    $operation=New-RAWMOperation 'Generating response locally' 180
    $cts=[Threading.CancellationTokenSource]::new()
    try {
        $response = Wait-RAWMTask ($client.SendAsync($request, [Net.Http.HttpCompletionOption]::ResponseHeadersRead, $cts.Token)) $operation
        Write-RAWMDebug 'response.headers' @{status=[int]$response.StatusCode; seconds=[Math]::Round($operation.Clock.Elapsed.TotalSeconds,2)}
        if (-not $response.IsSuccessStatusCode) {
            $detail = Wait-RAWMTask ($response.Content.ReadAsStringAsync($cts.Token)) $operation
            throw "Local model request failed ($([int]$response.StatusCode)): $detail"
        }
        $stream = Wait-RAWMTask ($response.Content.ReadAsStreamAsync($cts.Token)) $operation
        $reader = New-Object IO.StreamReader($stream)
        while ($true) {
            $line = Wait-RAWMTask ($reader.ReadLineAsync()) $operation -Quiet:($null -ne $firstToken)
            if ($null -eq $line) { break }
            if (-not $native -and -not $line.StartsWith('data:')) { continue }
            $data = if ($native) { $line.Trim() } else { $line.Substring(5).Trim() }
            if ($data -eq '[DONE]') { break }
            if (-not $data) { continue }
            $event = $data | ConvertFrom-Json
            if ($event.PSObject.Properties['usage'] -and $event.usage) { $usage = $event.usage }
            $piece = $null
            if ($native) {
                if ($event.PSObject.Properties['error']) { throw "Ollama failed: $($event.error)" }
                if ($event.PSObject.Properties['message']) { $piece=$event.message.content }
                if ($event.done) {
                    $usage=[pscustomobject]@{prompt_tokens=$event.prompt_eval_count; completion_tokens=$event.eval_count}
                    Write-RAWMDebug 'runtime.statistics' @{loadSeconds=[Math]::Round($event.load_duration/1e9,3); promptSeconds=[Math]::Round($event.prompt_eval_duration/1e9,3); generationSeconds=[Math]::Round($event.eval_duration/1e9,3); generationTokensPerSecond=$(if ($event.eval_duration -gt 0) {[Math]::Round($event.eval_count/($event.eval_duration/1e9),1)} else {0})} -Quiet
                }
            }
            if ($event.PSObject.Properties['choices'] -and $event.choices.Count -gt 0) {
                $delta = $event.choices[0].delta
                if ($delta -and $delta.PSObject.Properties['content']) { $piece = $delta.content }
            }
            if ($null -ne $piece -and $piece.Length -gt 0) {
                if (-not $firstToken) {
                    $firstToken = Get-Date
                    Write-RAWMDebug 'response.first_token' @{seconds=[Math]::Round(($firstToken-$started).TotalSeconds,2)}
                }
                $safe = Remove-RAWMControlSequence ([string]$piece)
                [void]$builder.Append($safe)
                Write-RAWMWrappedText -Text $safe -State $wrapState
            }
            if ($native -and $event.done) { break }
        }
        Write-RAWMWrappedText -Text '' -State $wrapState -Flush
        Write-Host
        if (-not $builder.ToString().Trim()) { throw 'The model returned an empty answer.' }
    } catch {
        Write-RAWMDebug 'response.failed' @{seconds=[Math]::Round($operation.Clock.Elapsed.TotalSeconds,2); kind=$_.Exception.GetType().Name}
        throw
    } finally {
        $cts.Cancel()
        if ($reader) { $reader.Dispose() }
        if ($stream) { $stream.Dispose() }
        if ($response) { $response.Dispose() }
        $request.Dispose(); $client.Dispose()
        $cts.Dispose(); Close-RAWMOperation $operation
    }
    $elapsed = ((Get-Date) - $started).TotalSeconds
    $answer = $builder.ToString().Trim()
    if (-not $answer) { throw 'The model returned an empty answer.' }
    $promptTokens = if ($usage) { [int]$usage.prompt_tokens } else { 0 }
    $completionTokens = if ($usage) { [int]$usage.completion_tokens } else { 0 }
    $speed = if ($elapsed -gt 0 -and $completionTokens -gt 0) { [Math]::Round($completionTokens / $elapsed, 1) } else { 0 }
    $script:LastUsage = [pscustomobject]@{ Prompt=$promptTokens; Completion=$completionTokens; Seconds=[Math]::Round($elapsed,2); TokensPerSecond=$speed; Model=$model.Name; Mode=$ModelMode }
    $script:LastAnswer = $answer
    Write-RAWMDebug 'response.completed' @{model=$model.Name; seconds=[Math]::Round($elapsed,2); firstTokenSeconds=[Math]::Round(($firstToken-$started).TotalSeconds,2); inputTokens=$promptTokens; outputTokens=$completionTokens; endToEndTokensPerSecond=$speed}
    $script:Session.totals.promptTokens += $promptTokens
    $script:Session.totals.completionTokens += $completionTokens
    $script:Session.totals.turns += 1
    return $answer
}

function Write-RAWMUsage {
    if (-not $script:LastUsage) { Write-RAWMColor 'No completed turn has usage data yet.' Gray; return }
    $u = $script:LastUsage
    Write-RAWMBox 'Usage' @("In: $($u.Prompt)  Out: $($u.Completion)  |  $($u.TokensPerSecond) tok/s  |  $($u.Seconds)s", "Mode: $($u.Mode)  |  $($u.Model)") 'Gray'
}

function Get-RAWMCodeBlock {
    param([string]$Text)
    $match = [regex]::Match($Text, '(?s)```[^\r\n]*\r?\n(.*?)```')
    if ($match.Success) { return $match.Groups[1].Value.TrimEnd() }
    return $null
}

function Set-RAWMClipboard {
    param([string]$Text)
    if (-not $Text) { throw 'There is nothing to copy.' }
    if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) { Set-Clipboard -Value $Text; return }
    $Text | clip.exe
}

function Read-RAWMMultiline {
    Write-RAWMColor 'Paste or type multiple lines. Enter a line containing only .send to submit; .cancel aborts.' Gray
    $lines = New-Object Collections.Generic.List[string]
    while ($true) {
        $line = Read-Host '...'
        if ($line -eq '.send') { return ($lines -join "`n") }
        if ($line -eq '.cancel') { return $null }
        $lines.Add($line)
    }
}

function Export-RAWMSession {
    $folder = Join-Path $script:Root 'exports'
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $path = Join-Path $folder ($script:Session.id + '.md')
    $sb = New-Object Text.StringBuilder
    [void]$sb.AppendLine("# $($script:Session.title)")
    foreach ($message in $script:Session.messages) {
        if ($message.role -eq 'system') { continue }
        [void]$sb.AppendLine(); [void]$sb.AppendLine("## $($message.role)"); [void]$sb.AppendLine(); [void]$sb.AppendLine([string]$message.content)
    }
    [IO.File]::WriteAllText($path, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
    return $path
}

function Get-RAWMChatMessages {
    param([string]$SystemInstruction)
    # Refresh policy for resumed sessions and reflect tool toggles on every turn.
    if (-not $SystemInstruction) {
        $behavior = Get-Content -LiteralPath (Join-Path $script:Root 'context\RAWM-BEHAVIOR.md') -Raw -Encoding UTF8
        $SystemInstruction = "Your application name is $(Get-RAWMPasscode). You are an AI assistant, not a human owner. This name is a display label, not the user's name.`n" + $behavior + "`nCurrent local capabilities: " + (Get-RAWMCapabilityText -ForModel)
    }
    @{role='system'; content=$SystemInstruction}
    $script:Session.messages | Where-Object { $_.role -ne 'system' }
}

function Show-RAWMHelp {
    Write-RAWMBox 'Commands' @(
        'Describe tasks normally, e.g. Open Notepad and write hello.',
        'When an action is proposed: y approves, n cancels.',
        '/new              Start a clean chat', '/resume [id]      Resume the newest or named chat',
        '/auto /fast /code Set model routing', '/model            Show configured models',
        '/workers          Show worker backends', '/worker auto|pi|qwen|codex|local  Choose one',
        '/usage            Show last and session usage', '/paste            Enter multiline input',
        '/debug [on|off|stats] Live activity and runtime statistics',
        '/passcode [name]   Show or change the app name (not a password)',
        '/copy             Copy last answer', '/copy code         Copy first code block',
        '/export           Export this chat to Markdown', '/stop             Stop the local model server',
        '/agent            Local actions, tools, and status', '/act <request>    Plan a local action',
        '/inspect "path"   Check a local text/code file',
        '/approve [id]     Run the displayed plan', '/cancel           Discard a pending plan',
        '/exit             Save and return to PowerShell') 'Cyan'
}

function Invoke-RAWMCommand {
    param([string]$InputText)
    $parts = $InputText.Trim().Split(@(' '), 2, [StringSplitOptions]::RemoveEmptyEntries)
    $command = $parts[0].ToLowerInvariant()
    $argument = if ($parts.Count -gt 1) { $parts[1] } else { '' }
    switch ($command) {
        '/passcode' {
            if ($argument) { Set-RAWMPasscode $argument; Write-RAWMColor "App name saved: $(Get-RAWMPasscode). It takes effect now and on restart." Green }
            else { Write-RAWMColor "Current app name: $(Get-RAWMPasscode). Change it with /passcode TZ. This is a display label, not an access password." Cyan }
        }
        '/debug' {
            if ($argument -eq 'on') { $script:DebugEnabled=$true }
            elseif ($argument -eq 'off') { $script:DebugEnabled=$false }
            elseif ($argument -and $argument -ne 'stats') { throw 'Use /debug, /debug stats, /debug on, or /debug off.' }
            Show-RAWMDebug
        }
        '/help' { Show-RAWMHelp }
        '/workers' { foreach ($line in (Get-RAWMWorkerSummary)) { Write-RAWMColor $line Gray } }
        '/worker' {
            $choice=$argument.Trim().ToLowerInvariant()
            if ($choice -notin @('auto','local','pi','qwen','codex')) { throw 'Use /worker auto, /worker local, /worker pi, /worker qwen, or /worker codex.' }
            $script:Worker.Default=$choice
            $script:Agent.Worker=$choice
            Write-RAWMColor ("Worker selection: " + $choice) Green
            foreach ($line in (Get-RAWMWorkerSummary)) { Write-RAWMColor $line Gray }
        }
        '/new' { Clear-RAWMPendingPlan; New-RAWMSession; Write-RAWMColor "New chat: $($script:Session.id)" Green }
        '/resume' { Clear-RAWMPendingPlan; Resume-RAWMSession $argument; Write-RAWMColor "Resumed: $($script:Session.id) - $($script:Session.title)" Green }
        '/auto' { $script:Mode='auto'; Write-RAWMColor 'Routing: AUTO' Green }
        '/fast' { $script:Mode='fast'; Write-RAWMColor 'Routing: FAST' Green }
        '/code' { $script:Mode='code'; Write-RAWMColor 'Routing: CODE' Green }
        '/model' { Show-TZModels $argument }
        '/models' { Show-TZModels $argument }
        '/usage' {
            Write-RAWMUsage
            Write-RAWMColor "Session: $($script:Session.totals.turns) turns, $($script:Session.totals.promptTokens) in, $($script:Session.totals.completionTokens) out" Gray
        }
        '/paste' { return [pscustomobject]@{ Handled=$true; Submit=(Read-RAWMMultiline) } }
        '/copy' {
            $copyText = if ($argument -eq 'code') { Get-RAWMCodeBlock $script:LastAnswer } else { $script:LastAnswer }
            Set-RAWMClipboard $copyText; Write-RAWMColor 'Copied.' Green
        }
        '/export' { $path=Export-RAWMSession; Write-RAWMColor "Exported: $path" Green }
        '/agent' {
            switch ($argument.Trim().ToLowerInvariant()) {
                'on' { $script:Agent.Enabled=$true; Show-RAWMAgent }
                'off' { Clear-RAWMPendingPlan; $script:Agent.Enabled=$false; Write-RAWMColor 'Agent OFF. Chat only.' Green }
                'audit' { Show-RAWMAgentAudit }
                'tools' { Show-RAWMAgent }
                '' { Show-RAWMAgent }
                default { throw 'Use /agent, /agent on, /agent off, /agent tools, or /agent audit.' }
            }
        }
        '/act' {
            if (-not $argument.Trim()) { throw 'Use /act followed by a local action request.' }
            $answer = Submit-RAWMAgentRequest $argument
            Write-RAWMColor $answer Green
        }
        '/inspect' {
            $inspection=ConvertFrom-RAWMInspectArgument $argument
            [void](Invoke-RAWMFileInspection -Path $inspection.Path -Question $inspection.Question)
        }
        '/approve' {
            $id = $argument.Trim()
            if (-not $id -and $script:Agent.Pending) { $id=$script:Agent.Pending.Id }
            $answer = Approve-RAWMPlan $id; Write-RAWMColor $answer Green
        }
        '/cancel' { Clear-RAWMPendingPlan; Write-RAWMColor 'Pending plan discarded.' Gray }
        '/stop' { Clear-RAWMPendingPlan; Stop-RAWMServer; Write-RAWMColor 'Local model stopped.' Amber }
        '/exit' { return [pscustomobject]@{ Handled=$true; Exit=$true } }
        default { Write-RAWMColor "Unknown command: $command. Use /help." Amber }
    }
    return [pscustomobject]@{ Handled=$true }
}

function Start-RAWMChat {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root, [string]$Mode='auto', [string]$Resume, [switch]$New, [switch]$NoBanner)
    $script:Root = (Resolve-Path -LiteralPath $Root).Path
    $script:Settings = Read-RAWMJson (Join-Path $script:Root 'config\settings.json')
    $localSettings = Join-Path $script:Root 'config\settings.local.json'
    if (Test-Path -LiteralPath $localSettings) { $script:Settings = Read-RAWMJson $localSettings }
    Assert-RAWMLocalBackend
    Initialize-RAWMAgent
    $script:Mode = $Mode
    if ($Resume) { Resume-RAWMSession $Resume } else { New-RAWMSession }
    if ($script:DebugEnabled) { Write-RAWMDebugLine 'enabled' @{statistics='/debug'; hide='/debug off'} }
    if (-not $NoBanner) {
        Write-RAWMBox (Get-RAWMPasscode) @('LOCAL  |  Private', "Routing: $($script:Mode.ToUpperInvariant())  |  Session: $($script:Session.id)", "Agent: $(if (-not $script:Agent.Enabled) {'OFF'} elseif (-not $script:Agent.Tools.Count) {'UNAVAILABLE'} else {'ON'})") 'Cyan'
    }
    try {
        while ($true) {
            Write-Host
            Write-RAWMColor "$(Get-RAWMPasscode) > " Cyan -NoNewline
            $inputText = [Console]::ReadLine()
            if ($null -eq $inputText) { break }
            if (-not $inputText.Trim()) { continue }
            $inputText = $inputText.Trim()
            $fromPaste = $false
            if ($inputText.StartsWith('/')) {
                try { $result = Invoke-RAWMCommand $inputText } catch { Write-RAWMColor $_.Exception.Message Red; continue }
                if ($result.PSObject.Properties['Exit'] -and $result.Exit) { break }
                if ($result.PSObject.Properties['Submit'] -and $null -ne $result.Submit) { $inputText = $result.Submit; $fromPaste = $true } else { continue }
                if (-not $inputText) { continue }
            }
            if (-not $fromPaste) {
                try {
                    $controlAnswer = Invoke-RAWMConversationControl $inputText
                    if ($null -ne $controlAnswer) {
                        if ($controlAnswer -ne 'Copied the last response to your clipboard.') { $script:LastAnswer = $controlAnswer }
                        Write-RAWMColor $controlAnswer Green
                        continue
                    }
                } catch { Write-RAWMColor $_.Exception.Message Red; continue }
            }
            $inspection = if (-not $fromPaste) { Get-RAWMFileInspectionIntent $inputText } else { $null }
            if ($inspection) {
                try { [void](Invoke-RAWMFileInspection -Path $inspection.Path -Question $inspection.Question) }
                catch { Write-RAWMColor $_.Exception.Message Red }
                continue
            }
            if (-not $fromPaste -and (Test-RAWMAgentIntent $inputText)) {
                try {
                    $answer = Submit-RAWMAgentRequest $inputText
                    $script:LastAnswer = $answer
                    Write-RAWMColor $answer Green
                } catch { Write-RAWMColor $_.Exception.Message Red }
                # Raw agent requests and file results stay out of conversation prompts and chat exports.
                continue
            }
            $modelMode = Get-RAWMModelMode $inputText
            Add-RAWMMessage 'user' $inputText
            Save-RAWMSession
            Write-Host
            Write-RAWMColor "$(Get-RAWMPasscode) | $($modelMode.ToUpperInvariant())" Green
            try {
                $answer = Invoke-RAWMCompletion $modelMode
                Add-RAWMMessage 'assistant' $answer
                Save-RAWMSession
                if ($script:Settings.interface.showUsageAfterEachTurn) { Write-Host; Write-RAWMUsage }
            } catch {
                if ($script:Session.messages.Count -gt 1 -and $script:Session.messages[$script:Session.messages.Count-1].role -eq 'user') {
                    $script:Session.messages.RemoveAt($script:Session.messages.Count-1)
                }
                Save-RAWMSession
                Write-RAWMColor $_.Exception.Message Red
            }
        }
    } finally {
        try { Clear-RAWMPendingPlan; Save-RAWMSession }
        finally { Stop-RAWMServer }
        Write-RAWMColor "$(Get-RAWMPasscode) closed. Back in PowerShell." Gray
    }
}

Export-ModuleMember -Function Start-RAWMChat
