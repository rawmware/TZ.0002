# Explicit live smoke test: opens one YouTube browser window and leaves it open.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root)
    $script:Root=$root
    $script:Settings=Read-RAWMJson (Join-Path $root 'config\settings.json')
    Initialize-RAWMAgent
    $request='hello - open chrome or the edge browser and open up youtube'
    $null=Submit-RAWMAgentRequest $request
    $result=Invoke-RAWMConversationControl 'y'
    if ($result -notlike 'Sent https://www.youtube.com/*') { throw $result }
    Write-Host $result
    Write-Host 'PASS: real browser process accepted the URL. Loading and page content require separate observation.'
} $root
