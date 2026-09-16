# Compatibility entry point. The installer and application now run in Python.
[CmdletBinding()]
param([switch]$SetupModel)
$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Install Python 3.10+ with PATH enabled, then run python install.py --setup-model --desktop.' }
$arguments = @((Join-Path $PSScriptRoot 'install.py'), '--desktop')
if ($SetupModel) { $arguments += '--setup-model' }
& $python.Source @arguments
if ($LASTEXITCODE -ne 0) { throw 'TZ installation failed; see the error above.' }
