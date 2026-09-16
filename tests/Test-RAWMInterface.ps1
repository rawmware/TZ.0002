[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root)
    $script:Root=$root
    $script:Settings=Read-RAWMJson (Join-Path $root 'config\settings.json')
    $script:checks=0
    function Check([bool]$Condition,[string]$Name) {
        if (-not $Condition) { throw "FAIL: $Name" }
        $script:checks++
    }
    Check ((Get-RAWMPasscode) -ceq 'roman') 'default passcode display identity'
    $script:Settings.interface.passcode='astra'
    Check ((Get-RAWMPasscode) -ceq 'astra') 'custom passcode display identity'
    $script:Settings.interface.passcode=('a' + [char]27 + '[31m' + 'stra')
    Check ((Get-RAWMPasscode) -ceq 'astra') 'control sequences removed from display identity'
    $fixture=Join-Path $root ('tests/.runs/identity-'+[guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory((Join-Path $fixture 'config'))
    $script:Root=$fixture
    $beforeModels=$script:Settings.models|ConvertTo-Json -Depth 10 -Compress
    Set-RAWMPasscode 'TZ'
    Check ((Get-RAWMPasscode) -ceq 'TZ') 'name changes immediately'
    $saved=Read-RAWMJson (Join-Path $fixture 'config/settings.local.json')
    Check ($saved.interface.passcode -ceq 'TZ') 'name persists on disk'
    Check (($saved.models|ConvertTo-Json -Depth 10 -Compress) -ceq $beforeModels) 'model settings preserved'
    $script:Settings=$saved
    Check ((Get-RAWMPasscode) -ceq 'TZ') 'name survives settings reload'
    foreach ($invalid in @('', ' ', ('x'*33), "bad`nname", 'bad/name', ('x'+[char]27+'[31m'))) {
        $rejected=$false
        try { Set-RAWMPasscode $invalid } catch { $rejected=$true }
        Check $rejected 'invalid name rejected'
    }
    Check ((Read-RAWMJson (Join-Path $fixture 'config/settings.local.json')).interface.passcode -ceq 'TZ') 'rejected names do not change disk'
    Set-RAWMPasscode 'My App'
    Check ((Get-RAWMPasscode) -ceq 'My App') 'names with spaces supported'
    Write-Host "PASS: $checks interface checks."
} $root
