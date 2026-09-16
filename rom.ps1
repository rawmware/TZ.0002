# Compatibility entry point for profiles that previously dot-sourced rom.ps1.
function global:Rom {
    & (Join-Path $PSScriptRoot 'Start-RAWM.ps1') @args
}
function global:Roman {
    & (Join-Path $PSScriptRoot 'Start-RAWM.ps1') @args
}
if ($MyInvocation.InvocationName -ne '.') { Rom @args }
