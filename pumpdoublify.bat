@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
    python "%~dp0pumpdoublify.py" %*
) else (
    py -3 "%~dp0pumpdoublify.py" %*
)

set "PUMPDOUBLIFY_EXIT=%errorlevel%"
if not "%PUMPDOUBLIFY_EXIT%"=="0" echo PumpDoublify exited with an error.
pause
exit /b %PUMPDOUBLIFY_EXIT%
