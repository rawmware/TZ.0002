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
    Write-Host "PASS: $checks interface checks."
} $root
