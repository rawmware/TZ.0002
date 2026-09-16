# Shared bounded waits. Never block on pipe EOF after a helper has already finished.
function New-RAWMOperation {
    param([string]$Label, [double]$TimeoutSeconds=120)
    $previous=$null
    try {
        if (-not [Console]::IsInputRedirected) {
            $previous=[Console]::TreatControlCAsInput
            [Console]::TreatControlCAsInput=$true
        }
    } catch {}
    return @{Label=$Label; Clock=[Diagnostics.Stopwatch]::StartNew(); Timeout=$TimeoutSeconds; NextProgress=5; Previous=$previous}
}

function Close-RAWMOperation {
    param($Operation)
    if ($null -ne $Operation.Previous) {
        try { [Console]::TreatControlCAsInput=[bool]$Operation.Previous } catch {}
    }
    $Operation.Clock.Stop()
}

function Update-RAWMOperation {
    param($Operation, [switch]$Quiet)
    if (Test-RAWMAgentCancelKey) { throw "$($Operation.Label) canceled. Returned to your prompt." }
    $seconds=$Operation.Clock.Elapsed.TotalSeconds
    if ($seconds -ge $Operation.Timeout) { throw "$($Operation.Label) timed out after $([int]$Operation.Timeout)s. No completion was verified." }
    if (-not $Quiet -and $seconds -ge $Operation.NextProgress) {
        Write-RAWMColor "$($Operation.Label) | $([int]$seconds)s elapsed | Esc or Ctrl+C cancels in this terminal." Gray
        $Operation.NextProgress=$seconds+5
    }
}

function Wait-RAWMTask {
    param($Task, $Operation, [switch]$Quiet)
    while (-not $Task.IsCompleted) {
        Update-RAWMOperation $Operation -Quiet:$Quiet
        Start-Sleep -Milliseconds 50
    }
    Update-RAWMOperation $Operation -Quiet:$Quiet
    # Preserve objects (not PowerShell's enumeration of their contents).
    return $Task.GetAwaiter().GetResult()
}

function Receive-RAWMProcess {
    param([Diagnostics.Process]$Process, $Operation, [switch]$SingleLine)
    $stdout=if ($SingleLine) { $Process.StandardOutput.ReadLineAsync() } else { $Process.StandardOutput.ReadToEndAsync() }
    $stderr=$Process.StandardError.ReadToEndAsync()
    while (-not $Process.HasExited) {
        Update-RAWMOperation $Operation
        Start-Sleep -Milliseconds 50
    }
    # All reads remain subject to the same deadline, including after process exit.
    $out=Wait-RAWMTask $stdout $Operation
    if ($SingleLine -and $Process.ExitCode -eq 0) { return [string]$out }
    $err=Wait-RAWMTask $stderr $Operation
    if ($Process.ExitCode -ne 0) {
        $detail=if ($err) { Remove-RAWMControlSequence ([string]$err) } else { 'No diagnostic was returned.' }
        if ($detail.Length -gt 2000) { $detail=$detail.Substring(0,2000) }
        throw "$($Operation.Label) failed: $detail"
    }
    return [string]$out
}

function Invoke-RAWMLocalJson {
    param($Body, [string]$Label, [int]$TimeoutSeconds=120)
    $operation=New-RAWMOperation $Label $TimeoutSeconds
    $client=[Net.Http.HttpClient]::new([Net.Http.HttpClientHandler]@{UseProxy=$false;AllowAutoRedirect=$false})
    $client.Timeout=[TimeSpan]::FromSeconds($TimeoutSeconds)
    $cts=[Threading.CancellationTokenSource]::new()
    $content=[Net.Http.StringContent]::new(($Body|ConvertTo-Json -Depth 30 -Compress),[Text.Encoding]::UTF8,'application/json')
    $response=$null
    try {
        $task=$client.PostAsync(((Get-RAWMBackendUrl)+'/v1/chat/completions'),$content,$cts.Token)
        $response=Wait-RAWMTask $task $operation
        if (-not $response.IsSuccessStatusCode) { throw "$Label failed (HTTP $([int]$response.StatusCode))." }
        $json=Wait-RAWMTask ($response.Content.ReadAsStringAsync($cts.Token)) $operation
        return ConvertFrom-Json -InputObject $json -AsHashtable
    } finally {
        $cts.Cancel()
        if ($response) { $response.Dispose() }
        $content.Dispose(); $client.Dispose(); $cts.Dispose()
        Close-RAWMOperation $operation
    }
}
