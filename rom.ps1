# Compatibility wrapper. TZ.cmd is the only application entry point.
function global:Rom { & (Join-Path $PSScriptRoot 'TZ.cmd') @args }
function global:Roman { & (Join-Path $PSScriptRoot 'TZ.cmd') @args }
if ($MyInvocation.InvocationName -ne '.') { & (Join-Path $PSScriptRoot 'TZ.cmd') @args }
