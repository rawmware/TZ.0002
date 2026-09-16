@echo off
setlocal
where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0tz.py" %*
  exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0tz.py" %*
  exit /b
)
echo TZ needs Python 3.10 or newer. Install Python and enable its PATH option.
pause
exit /b 1
