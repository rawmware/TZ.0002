[CmdletBinding()]
param(
    [ValidateSet('auto', 'fast', 'code')]
    [string]$Mode = 'auto',
    [string]$Resume,
    [switch]$New,
    [switch]$NoBanner
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) {
    $modernShell = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    $modernShellPath = if ($modernShell) { $modernShell.Source } else {
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    }
    if (-not (Test-Path -LiteralPath $modernShellPath -PathType Leaf)) {
        throw 'RAWM requires PowerShell 7. Install PowerShell 7 and run roman again.'
    }
    $forward = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $MyInvocation.MyCommand.Path, '-Mode', $Mode)
    if ($Resume) { $forward += @('-Resume', $Resume) }
    if ($New) { $forward += '-New' }
    if ($NoBanner) { $forward += '-NoBanner' }
    & $modernShellPath @forward
    return
}
$rawmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $rawmRoot 'app\RAWM.psm1'

if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "RAWM module is missing: $modulePath"
}

Import-Module $modulePath -Force
Start-RAWMChat -Root $rawmRoot -Mode $Mode -Resume $Resume -New:$New -NoBanner:$NoBanner
