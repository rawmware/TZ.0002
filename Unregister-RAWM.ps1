[CmdletBinding()]
param([switch]$AllPowerShellEditions)

$ErrorActionPreference = 'Stop'
$begin = '# >>> RAWM portable launcher >>>'
$end = '# <<< RAWM portable launcher <<<'
$targets = @($PROFILE.CurrentUserCurrentHost)
if ($AllPowerShellEditions) {
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\Microsoft.PowerShell_profile.ps1')
}
foreach ($profilePath in ($targets | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $profilePath)) { continue }
    $existing = Get-Content -LiteralPath $profilePath -Raw
    $pattern = '(?s)\s*' + [regex]::Escape($begin) + '.*' + [regex]::Escape($end) + '\s*'
    $updated = [regex]::Replace($existing, $pattern, "`r`n").TrimEnd() + "`r`n"
    [IO.File]::WriteAllText($profilePath, $updated, (New-Object Text.UTF8Encoding($false)))
    Write-Host "Removed RAWM registration from $profilePath" -ForegroundColor Green
}
$shimPath = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\roman.cmd'
$launcherPath = Join-Path $env:LOCALAPPDATA 'RAWM\Launch-RAWM.ps1'
if (Test-Path -LiteralPath $shimPath) { Remove-Item -LiteralPath $shimPath -Force }
if (Test-Path -LiteralPath $launcherPath) { Remove-Item -LiteralPath $launcherPath -Force }
