# Remove only this bridge's registration; preserve application and user data.
$ErrorActionPreference='Stop'
$bin=Join-Path $env:LOCALAPPDATA 'TZ\bin'
$state=Join-Path $env:LOCALAPPDATA 'TZ/registration.json'
if (-not (Test-Path $state)) { throw 'No desktop bridge registration backup found.' }
$saved=Get-Content -LiteralPath $state -Raw | ConvertFrom-Json
$parts=@([Environment]::GetEnvironmentVariable('Path','User') -split ';' | Where-Object { $_ -and $_.TrimEnd('\','/') -ine $bin.TrimEnd('\','/') })
[Environment]::SetEnvironmentVariable('Path',($parts -join ';'),'User')
if ([Environment]::GetEnvironmentVariable('TZ_HOME','User') -eq $PSScriptRoot) {
    [Environment]::SetEnvironmentVariable('TZ_HOME',$saved.TZ_HOME,'User')
}
foreach ($name in @('roman.cmd','rom.cmd')) {
    $path=Join-Path $bin $name
    if (Test-Path $path) { Remove-Item -LiteralPath $path }
}
foreach ($folder in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))) {
    $path=Join-Path $folder 'Roman TZ.lnk'
    if (Test-Path $path) { Remove-Item -LiteralPath $path }
}
Write-Host 'Desktop registration removed. App, chats, models and backups remain. Restore the helper backup described in source0001.md and sign out/in to refresh the environment.'
