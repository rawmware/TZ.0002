[CmdletBinding()]
param([string]$FastModel='gemma3:1b', [string]$CodeModel='qwen3.6:latest', [switch]$SkipModelCheck)
$ErrorActionPreference='Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this installer in PowerShell 7.' }
$root=$PSScriptRoot
$bin=Join-Path $env:LOCALAPPDATA 'TZ\bin'
$state=Join-Path $env:LOCALAPPDATA 'TZ\registration.json'
$shell=(Get-Process -Id $PID).Path
$localConfig=Join-Path $root 'config/settings.local.json'
$settings=Get-Content (Join-Path $root 'config/settings.json') -Raw | ConvertFrom-Json
$settings.backend.type='ollama'
$settings.backend.port=11434
$settings.models.fast.name=$FastModel
$settings.models.code.name=$CodeModel
if (-not $SkipModelCheck) {
    $tags=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 -NoProxy
    foreach ($model in @($FastModel,$CodeModel)) {
        if ($model -cnotin @($tags.models.name)) { throw "Model '$model' is missing. Check ollama list." }
    }
}
New-Item -ItemType Directory -Path $bin -Force | Out-Null
if (-not (Test-Path $state)) {
    @{UserPath=[Environment]::GetEnvironmentVariable('Path','User'); TZ_HOME=[Environment]::GetEnvironmentVariable('TZ_HOME','User')} |
        ConvertTo-Json | Set-Content -LiteralPath $state -Encoding utf8
}
if (Test-Path $localConfig) { Copy-Item $localConfig ($localConfig+'.backup-'+(Get-Date -Format yyyyMMddHHmmss)) }
$settings | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $localConfig -Encoding utf8
$shim=@'
@echo off
setlocal
if not defined TZ_HOME set "TZ_HOME=__ROOT__"
"__SHELL__" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TZ_HOME%\Start-RAWM.ps1" %*
exit /b %errorlevel%
'@
$shim=$shim.Replace('__ROOT__',$root.Replace('%','%%')).Replace('__SHELL__',$shell.Replace('%','%%'))
foreach ($name in @('roman.cmd','rom.cmd')) { [IO.File]::WriteAllText((Join-Path $bin $name),$shim,[Text.Encoding]::ASCII) }
$userPath=[Environment]::GetEnvironmentVariable('Path','User')
$parts=@($userPath -split ';' | Where-Object { $_ -and $_.TrimEnd('\') -ine $bin.TrimEnd('\') })
[Environment]::SetEnvironmentVariable('Path',(@($bin)+$parts -join ';'),'User')
[Environment]::SetEnvironmentVariable('TZ_HOME',$root,'User')
$env:TZ_HOME=$root
$env:Path=$bin+';'+$env:Path
$shortcuts=New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))) {
    $shortcut=$shortcuts.CreateShortcut((Join-Path $folder 'Roman TZ.lnk'))
    $shortcut.TargetPath=$shell
    $shortcut.Arguments='-NoLogo -NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $root 'Start-RAWM.ps1')+'"'
    $shortcut.WorkingDirectory=$root
    $shortcut.Save()
}
# Notify Explorer so new terminals inherit the updated user environment.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TZEnvironment {
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, UIntPtr w, string l, uint f, uint t, out UIntPtr r);
}
'@
$result=[UIntPtr]::Zero
[void][TZEnvironment]::SendMessageTimeout([IntPtr]0xffff,0x1a,[UIntPtr]::Zero,'Environment',2,5000,[ref]$result)
Write-Host "Installed in $root. Open Roman TZ from Start/Desktop, or type roman in a new terminal."
