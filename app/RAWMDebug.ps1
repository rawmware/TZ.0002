$script:DebugEnabled = $true
$script:DebugEvents = [Collections.Generic.List[object]]::new()

function Write-RAWMDebugLine {
    param([string]$Stage, [hashtable]$Metrics=@{})
    $status=[string]$Metrics['status']
    $color=if ($Stage -match 'failed|error' -or $status -eq 'failed') {'Red'}
        elseif ($Stage -match 'completed' -or $status -eq 'verified') {'Green'}
        elseif ($Stage -match 'waiting|agent|tool' -or $status -match 'canceled|reported|launched') {'Amber'}
        else {'Cyan'}
    $state=@{Pending='';Column=0}
    # Emit ANSI separately so wrapping counts visible characters only.
    foreach ($part in @(@('Red','● '),@('Cyan','LIVE DEBUG '),@($color,"$Stage "))) {
        $nativeColor=if ($part[0] -eq 'Amber') {'Yellow'} else {$part[0]}
        Write-RAWMWrappedText -Text $part[1] -State $state -Flush -Color $nativeColor
    }
    foreach ($item in ($Metrics.GetEnumerator()|Sort-Object Key)) {
        Write-RAWMWrappedText -Text "| $($item.Key)=" -State $state -Flush -Color DarkGray
        Write-RAWMWrappedText -Text ((Remove-RAWMControlSequence ([string]$item.Value))+' ') -State $state -Flush -Color White
    }
    Write-Host
}

function Write-RAWMDebug {
    param([string]$Stage, [hashtable]$Metrics=@{}, [switch]$Quiet)
    $record = [ordered]@{time=[DateTimeOffset]::UtcNow.ToString('o'); pid=$PID; stage=$Stage; metrics=$Metrics}
    $script:DebugEvents.Add($record)
    if ($script:DebugEvents.Count -gt 1000) { $script:DebugEvents.RemoveAt(0) }
    # Telemetry never includes prompts, file contents, arguments, or model output.
    try {
        if ($script:Root) {
            $folder=Join-Path $script:Root 'data/debug'
            [void][IO.Directory]::CreateDirectory($folder)
            $path=Join-Path $folder ("activity-$PID.jsonl")
            if ((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 5MB) {
                Move-Item -LiteralPath $path -Destination "$path.previous" -Force
            }
            [IO.File]::AppendAllText($path, (($record|ConvertTo-Json -Depth 6 -Compress)+"`n"))
        }
    } catch { } # Diagnostics must not break an action.
    if ($script:DebugEnabled -and -not $Quiet) {
        Write-RAWMDebugLine $Stage $Metrics
    }
}

function Show-RAWMDebug {
    if ($script:DebugEnabled) { Write-RAWMDebugLine 'enabled' @{cyan='request stages'; green='completed'; amber='agent / tools / waiting'; red='errors'} }
    $completed=@($script:DebugEvents | Where-Object stage -eq 'response.completed')
    $failed=@($script:DebugEvents | Where-Object stage -eq 'response.failed')
    $lines=@("Live activity: $($script:DebugEnabled) | /debug on or /debug off", "Completed responses: $($completed.Count) | Failed/canceled responses: $($failed.Count)")
    if ($completed.Count) {
        $times=@($completed | ForEach-Object { [double]$_.metrics.seconds } | Sort-Object)
        $sum=($times|Measure-Object -Sum -Average)
        $p95=$times[[Math]::Max(0,[int][Math]::Ceiling($times.Count*0.95)-1)]
        $tokens=($completed|ForEach-Object { [int]$_.metrics.outputTokens }|Measure-Object -Sum).Sum
        $lines += "Latency mean: $([Math]::Round($sum.Average,2))s | p95: $($p95)s | Output tokens: $tokens"
    }
    $lines += "Statistics cover the last 1,000 events in this process. Logs: data/debug/activity-$PID.jsonl"
    $tools=@($script:DebugEvents | Where-Object { $_.stage -eq 'agent.event' -and $_.metrics.event -eq 'tool' })
    $lines += "Tool events: started=$(@($tools|Where-Object {$_.metrics.status -eq 'started'}).Count), verified=$(@($tools|Where-Object {$_.metrics.status -eq 'verified'}).Count), failed=$(@($tools|Where-Object {$_.metrics.status -eq 'failed'}).Count)"
    $lines += "Tool outcomes: launched=$(@($tools|Where-Object {$_.metrics.status -eq 'launched'}).Count), worker-reported=$(@($tools|Where-Object {$_.metrics.status -eq 'reported'}).Count)"
    $runtime=@($script:DebugEvents | Where-Object stage -eq 'runtime.statistics' | Select-Object -Last 1)
    if ($runtime.Count) {
        $m=$runtime[0].metrics
        $lines += "Last runtime: load=$($m.loadSeconds)s | prompt=$($m.promptSeconds)s | generation=$($m.generationSeconds)s | $($m.generationTokensPerSecond) generation tok/s"
    }
    $operations=@($script:DebugEvents | Where-Object stage -eq 'operation.ended' | Select-Object -Last 5)
    foreach ($op in $operations) { $lines += "Recent operation: $($op.metrics.operation) | $($op.metrics.seconds)s (ended, not proof of success)" }
    $lines += 'Activity describes observable operations; worker internals are unavailable unless reported.'
    Write-RAWMBox 'Live debugger / statistics' $lines Cyan
}
