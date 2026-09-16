[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root)
    $script:Root=$root
    $script:Settings=Read-RAWMJson (Join-Path $root 'config\settings.json')
    Initialize-RAWMAgent
    $script:Checks=0
    function Check([bool]$Value,[string]$Name) { if (-not $Value) { throw "FAIL: $Name" }; $script:Checks++ }
    $status=@(Get-RAWMWorkerStatus)
    Check ($status.Backend -contains 'pi' -and $status.Backend -contains 'qwen' -and $status.Backend -contains 'codex' -and $status.Backend -contains 'local') 'worker registry'
    Check ((Get-RAWMSelectedWorker).Backend -in @('pi','qwen','codex','local')) 'worker selection'
    $codexSpec=Get-RAWMWorkerProcessSpec 'codex' 'reply READY'
    Check ($codexSpec.Args[0] -ceq '--ask-for-approval' -and $codexSpec.Args[1] -ceq 'never' -and $codexSpec.Args[2] -ceq 'exec') 'codex noninteractive approval flags'
    foreach ($request in @('open vs code and write a simple c program','create a futuristic html website for me','open C:\Users\ROMAN\Downloads\ps2_deathbydegrees.jpg')) {
        Check (Test-RAWMWorkerIntent $request) "worker intent: $request"
        $answer=Submit-RAWMAgentRequest $request
        Check ($answer -like 'Approve: y*' -and $script:Agent.Pending.Json -like '*worker.delegate*') 'delegation waits for approval'
        Check ((Invoke-RAWMConversationControl 'n') -ceq 'Canceled. No actions ran.') 'delegation cancellation'
        Check ($null -eq $script:Agent.Pending) 'cancellation clears delegated work'
    }
    $plan=New-RAWMSinglePlan 'worker.delegate' @{backend='pi';prompt='reply READY'}
    Check (Assert-RAWMPlan $plan) 'delegation requires approval'
    foreach ($bad in @('shell','local','unknown')) {
        $badPlan=New-RAWMSinglePlan 'worker.delegate' @{backend=$bad;prompt='reply READY'}
        $rejected=$false; try { Assert-RAWMPlan $badPlan | Out-Null } catch { $rejected=$true }
        Check $rejected "invalid backend $bad"
    }
    Write-Host "PASS: $($script:Checks) worker checks. Pi/Qwen/Codex execution remains an explicit live integration check."
} $root
