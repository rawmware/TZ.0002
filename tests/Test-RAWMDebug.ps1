param([switch]$Live)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'app/RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root,$live)
    $script:Root=Join-Path $root ('tests/.runs/debug-'+[guid]::NewGuid().ToString('N'))
    $script:Settings=Read-RAWMJson (Join-Path $root 'config/settings.local.json')
    $script:DebugEnabled=$false
    $script:DebugEvents.Clear()
    Write-RAWMDebug 'response.completed' @{seconds=1; outputTokens=10}
    Write-RAWMDebug 'response.completed' @{seconds=3; outputTokens=20}
    Write-RAWMDebug 'response.failed' @{seconds=2; kind='TimeoutException'}
    function Write-RAWMBox { param($Title,$Lines,$Color); $script:DebugTestDisplay=$Lines -join "`n" }
    Show-RAWMDebug
    $display=$script:DebugTestDisplay
    if ($display -notmatch 'mean: 2s' -or $display -notmatch 'p95: 3s' -or $display -notmatch 'Output tokens: 30' -or $display -notmatch 'Failed/canceled responses: 1') { throw 'Statistics regression.' }
    for ($i=0;$i -lt 1005;$i++) { Write-RAWMDebug 'test.event' @{index=$i} -Quiet }
    if ($script:DebugEvents.Count -ne 1000) { throw 'Event retention is unbounded.' }
    $log=Get-Content (Join-Path $script:Root "data/debug/activity-$PID.jsonl") | ConvertFrom-Json
    if ($log.Count -ne 1008 -or $log[0].stage -ne 'response.completed') { throw 'JSONL telemetry missing.' }
    if ($live) {
        Copy-Item (Join-Path $root 'context') (Join-Path $script:Root 'context') -Recurse
        Initialize-RAWMAgent
        New-RAWMSession
        Add-RAWMMessage user 'hello?'
        $answer=Invoke-RAWMCompletion fast
        if (-not $answer -or $script:LastUsage.Completion -le 0) { throw 'Live completion missing output or usage.' }
        if (-not @($script:DebugEvents|Where-Object stage -eq 'runtime.statistics').Count) { throw 'Native runtime metrics missing.' }
        if ($script:LastUsage.Seconds -gt 15) { throw 'FAST greeting exceeded 15 seconds.' }
        Write-Host "Live greeting: $($script:LastUsage.Seconds)s"
    }
    Write-Host "PASS: debugger statistics, bounded retention, JSONL logging$(if ($live) {', native Ollama greeting and token usage'})."
} $root $Live
