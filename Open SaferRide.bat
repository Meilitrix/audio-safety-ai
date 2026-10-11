@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  Open SaferRide.bat - double-click to start the ride app
REM ══════════════════════════════════════════════════════════════════════
REM Starts the audio brain if it is not already up, then the SaferRide dev
REM server, then opens the page.  Safe to double-click repeatedly.
REM
REM "powershell" is called by ABSOLUTE PATH on purpose: this machine's PATH has
REM lost its Windows system folders, so the bare command fails with
REM   'powershell' is not recognized as an internal or external command
REM which looked like the app being broken when it was not.

setlocal
set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=%WINDIR%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" (
    echo Could not find PowerShell in either of the usual places.
    echo   %WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe
    echo   %WINDIR%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe
    pause
    exit /b 1
)

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_saferide.ps1" %*
endlocal
