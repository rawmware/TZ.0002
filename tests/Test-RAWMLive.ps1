[CmdletBinding()]
param([switch]$Notepad, [switch]$Model, [switch]$ChatOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fixture=Join-Path $PSScriptRoot ('.runs\live-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
foreach ($name in @('app','context','config')) { Copy-Item -LiteralPath (Join-Path $root $name) -Destination $fixture -Recurse }
Copy-Item -LiteralPath (Join-Path $root 'Start-RAWM.ps1') -Destination $fixture
$settings=Get-Content -LiteralPath (Join-Path $fixture 'config\settings.json') -Raw | ConvertFrom-Json
foreach ($mode in @('fast','code')) { $settings.models.$mode.file=Join-Path $root $settings.models.$mode.file }
$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
$listener.Start()
$settings.backend.port=$listener.LocalEndpoint.Port
$listener.Stop()
$settings.interface.unicodeBorders=$false
if ($Model -or $ChatOnly) {
    [void][IO.Directory]::CreateDirectory((Join-Path $fixture 'runtime'))
    Copy-Item -LiteralPath (Join-Path $root 'runtime\llama.cpp') -Destination (Join-Path $fixture 'runtime') -Recurse
}
[IO.File]::WriteAllText((Join-Path $fixture 'config\settings.json'),($settings|ConvertTo-Json -Depth 8))
Import-Module (Join-Path $fixture 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($fixture,$settings,$notepad,$model,$chatOnly)
    $script:Root=$fixture; $script:Settings=$settings
    Initialize-RAWMAgent
    $results=@{fixture=$fixture;port=$settings.backend.port}
    try {
        if ($notepad) {
            $preview=Submit-RAWMAgentRequest 'Open Notepad and write hello green world'
            if ($preview -notlike 'Approve: y*' -or -not $script:Agent.Pending) { throw 'Notepad did not wait for approval.' }
            $result=Invoke-RAWMConversationControl 'y'
            Write-Host $result
            if ($result -notlike 'Opened Notepad and verified 17 characters*') { throw "Notepad verification failed: $result" }
            $drafts=@(Get-ChildItem -LiteralPath (Join-Path $script:Agent.Storage 'drafts') -Filter '*.txt')
            if ($drafts.Count -ne 1 -or $drafts[0].Length -ne 0) { throw 'Notepad scratch file verification failed.' }
            $results.notepad=$result
        }
        if ($model) {
            New-RAWMSession
            # Capture candidate plans in this disposable test fixture to diagnose local-model mistakes.
            $script:LiveValidator=(Get-Command Assert-RAWMPlan).ScriptBlock
            function Assert-RAWMPlan {
                param($Plan)
                [IO.File]::WriteAllText((Join-Path $script:Root 'candidate-plan.json'),($Plan|ConvertTo-Json -Depth 12))
                & $script:LiveValidator $Plan
            }
            $request='Create a file named greeting.txt containing exactly Hello Roman'
            $result=Submit-RAWMAgentRequest $request -ModelOnly
            Write-Host $result
            if (-not $script:Agent.Pending) { throw 'Model plan did not wait for approval.' }
            if (Test-Path -LiteralPath (Join-Path $script:Agent.Workspace 'greeting.txt')) { throw 'Model plan ran before approval.' }
            $plan=$script:Agent.Pending.Json|ConvertFrom-Json -AsHashtable
            if ($plan.steps.Count -ne 1 -or $plan.steps[0].tool -ne 'file.create' -or $plan.steps[0].arguments.path -cne 'greeting.txt' -or $plan.steps[0].arguments.text -cne 'Hello Roman') {
                throw ('Planner produced an unexpected plan: ' + $script:Agent.Pending.Json)
            }
            $result=Approve-RAWMPlan $script:Agent.Pending.Id
            Write-Host $result
            if ([IO.File]::ReadAllText((Join-Path $script:Agent.Workspace 'greeting.txt')) -cne 'Hello Roman') { throw 'Approved model action failed.' }
            $results.model='Local model produced the exact file plan; no write before approval; approved result verified.'
            $sample=Join-Path $fixture 'sample.py'
            $code="def add(a, b):`n    return a - b`n"
            [IO.File]::WriteAllText($sample,$code)
            $hash=(Get-FileHash -LiteralPath $sample).Hash
            $answer=Invoke-RAWMFileInspection -Path $sample -Question 'This function should add two numbers. Identify the bug and give the corrected expression in one sentence.'
            if ($answer -notmatch 'a\s*\+\s*b|addition|subtract') { throw 'Local file review did not identify the arithmetic bug.' }
            if ((Get-FileHash -LiteralPath $sample).Hash -cne $hash) { throw 'File inspection modified its source.' }
            if (($script:Session.messages|ConvertTo-Json -Depth 8) -match 'BEGIN UNTRUSTED FILE CONTENT') { throw 'Raw file prompt leaked into saved history.' }
            $results.inspection=$answer
            $result=Submit-RAWMAgentRequest 'Create a file named first.txt containing exactly alpha, then rename first.txt to second.txt.' -ModelOnly
            $plan=$script:Agent.Pending.Json|ConvertFrom-Json -AsHashtable
            if ($plan.steps.Count -ne 2 -or $plan.steps[0].tool -ne 'file.create' -or $plan.steps[0].arguments.path -cne 'first.txt' -or $plan.steps[0].arguments.text -cne 'alpha' -or $plan.steps[1].tool -ne 'file.rename' -or $plan.steps[1].arguments.path -cne 'first.txt' -or $plan.steps[1].arguments.destination -cne 'second.txt') {
                throw ('Unexpected multi-step plan: ' + $script:Agent.Pending.Json)
            }
            if (Test-Path -LiteralPath (Join-Path $script:Agent.Workspace 'first.txt')) { throw 'Multi-step plan ran before approval.' }
            $result=Approve-RAWMPlan $script:Agent.Pending.Id
            Write-Host $result
            if ([IO.File]::ReadAllText((Join-Path $script:Agent.Workspace 'second.txt')) -cne 'alpha' -or (Test-Path -LiteralPath (Join-Path $script:Agent.Workspace 'first.txt'))) { throw 'Multi-step workflow failed.' }
            $results.multistep='Local model planned create then rename; approval and both verifications passed.'
            $blocked=$false
            try { [void](Submit-RAWMAgentRequest 'Delete all files in the workspace.' -ModelOnly) } catch { $blocked=$true }
            if (-not $blocked -or $script:Agent.Pending -or -not (Test-Path -LiteralPath (Join-Path $script:Agent.Workspace 'second.txt'))) { throw 'Unsupported destructive request was not rejected.' }
            $results.unsupported='Unsupported deletion request rejected without execution.'
        }
        if ($model -or $chatOnly) {
            New-RAWMSession
            Add-RAWMMessage 'user' 'Reply with the single word ready.'
            $answer=Invoke-RAWMCompletion fast
            if ($answer.Trim() -notmatch '^(?i)ready[.!]?$') { throw 'Chat smoke test did not return the requested word.' }
            $results.chat=$answer
        }
    } finally {
        Stop-RAWMServer
        [IO.File]::WriteAllText((Join-Path $fixture 'results.json'),($results|ConvertTo-Json -Depth 8))
    }
    Write-Host "PASS: live verification. Results: $fixture\results.json"
} $fixture $settings $Notepad $Model $ChatOnly
