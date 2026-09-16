[CmdletBinding()]
param([switch]$AllPowerShellEditions)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifest = Join-Path $root 'RAWM.portable.json'
if (-not (Test-Path -LiteralPath $manifest)) { throw "This is not a RAWM package: $root" }

$startPath = Join-Path $root 'Start-RAWM.ps1'
$escapedStart = $startPath.Replace("'", "''")
$relativeFolder = (Split-Path -Leaf $root).Replace("'", "''")
$begin = '# >>> RAWM portable launcher >>>'
$end = '# <<< RAWM portable launcher <<<'
$template = @'
__BEGIN__
function global:roman {
    $rawmStart = '__START__'
    if (-not (Test-Path -LiteralPath $rawmStart -PathType Leaf)) {
        $rawmStart = Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
            $candidateRoot = Join-Path $_.Root '__FOLDER__'
            $candidateManifest = Join-Path $candidateRoot 'RAWM.portable.json'
            if (Test-Path -LiteralPath $candidateManifest -PathType Leaf) {
                try {
                    $manifest = Get-Content -LiteralPath $candidateManifest -Raw | ConvertFrom-Json
                    if ($manifest.packageId -eq 'rawm-portable-roman-v1') { Join-Path $candidateRoot 'Start-RAWM.ps1' }
                } catch {}
            }
        } | Select-Object -First 1
    }
    if (-not $rawmStart) {
        Write-Host 'RAWM was not found. Connect the portable SSD or run Register-RAWM.ps1 again.' -ForegroundColor Yellow
        return
    }
    & $rawmStart @args
}
__END__
'@
$block = $template.Replace('__BEGIN__',$begin).Replace('__END__',$end).Replace('__START__',$escapedStart).Replace('__FOLDER__',$relativeFolder)

$targets = @($PROFILE.CurrentUserCurrentHost)
if ($AllPowerShellEditions) {
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
    $targets += (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\Microsoft.PowerShell_profile.ps1')
}
$targets = $targets | Select-Object -Unique

foreach ($profilePath in $targets) {
    $folder = Split-Path -Parent $profilePath
    if (-not (Test-Path -LiteralPath $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
    $existing = if (Test-Path -LiteralPath $profilePath) { Get-Content -LiteralPath $profilePath -Raw } else { '' }
    if ($existing -match [regex]::Escape($begin)) {
        $pattern = '(?s)' + [regex]::Escape($begin) + '.*' + [regex]::Escape($end)
        $literalBlock = $block.Trim()
        $updated = [regex]::Replace($existing, $pattern, { param($match) $literalBlock })
    } else {
        if ($existing -and -not $existing.EndsWith("`n")) { $existing += "`r`n" }
        $updated = $existing + $block
    }
    if (Test-Path -LiteralPath $profilePath) {
        Copy-Item -LiteralPath $profilePath -Destination ($profilePath + '.rawm-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    }
    [IO.File]::WriteAllText($profilePath, $updated, (New-Object Text.UTF8Encoding($false)))
    Write-Host "Registered roman in $profilePath" -ForegroundColor Green
}

# Windows PowerShell can be centrally configured to reject all profile scripts.
# A tiny command shim keeps `roman` available in that case and launches in-place.
$launcherFolder = Join-Path $env:LOCALAPPDATA 'RAWM'
$commandFolder = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
New-Item -ItemType Directory -Path $launcherFolder,$commandFolder -Force | Out-Null
$launcherPath = Join-Path $launcherFolder 'Launch-RAWM.ps1'
$launcherTemplate = @'
param(
    [ValidateSet('auto','fast','code')][string]$Mode='auto',
    [string]$Resume,
    [switch]$New,
    [switch]$NoBanner
)
$rawmStart = '__START__'
if (-not (Test-Path -LiteralPath $rawmStart -PathType Leaf)) {
    $rawmStart = Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
        $candidateRoot = Join-Path $_.Root '__FOLDER__'
        $candidateManifest = Join-Path $candidateRoot 'RAWM.portable.json'
        if (Test-Path -LiteralPath $candidateManifest -PathType Leaf) {
            try {
                $manifest = Get-Content -LiteralPath $candidateManifest -Raw | ConvertFrom-Json
                if ($manifest.packageId -eq 'rawm-portable-roman-v1') { Join-Path $candidateRoot 'Start-RAWM.ps1' }
            } catch {}
        }
    } | Select-Object -First 1
}
if (-not $rawmStart) { Write-Host 'RAWM was not found. Connect the portable SSD or register it again.' -ForegroundColor Yellow; exit 2 }
& $rawmStart -Mode $Mode -Resume $Resume -New:$New -NoBanner:$NoBanner
'@
$launcherContent = $launcherTemplate.Replace('__START__',$escapedStart).Replace('__FOLDER__',$relativeFolder)
[IO.File]::WriteAllText($launcherPath, $launcherContent, (New-Object Text.UTF8Encoding($false)))
$escapedLauncher = $launcherPath.Replace('%','%%')
$shim = "@echo off`r`nwhere pwsh.exe >nul 2>nul`r`nif %errorlevel%==0 (`r`n  pwsh.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedLauncher`" %*`r`n) else (`r`n  powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$escapedLauncher`" %*`r`n)`r`n"
[IO.File]::WriteAllText((Join-Path $commandFolder 'roman.cmd'), $shim, [Text.Encoding]::ASCII)

Write-Host 'Open a new PowerShell window and type: roman' -ForegroundColor Cyan
