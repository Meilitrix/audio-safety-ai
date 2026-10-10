@echo off
rem ══════════════════════════════════════════════════════════════════════
rem  Open Audio Safety.bat  -  double-click to start the brain and open the
rem  dashboard.  All the logic lives in launch_audio_safety.ps1 beside it.
rem
rem  PowerShell is called by ABSOLUTE path on purpose: this machine's PATH
rem  has lost its Windows system folders, so the bare word "powershell" is
rem  not recognised by a double-clicked window.  Nothing else is different.
rem ══════════════════════════════════════════════════════════════════════
title Audio Safety AI

set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=%WINDIR%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" (
  echo ERROR: PowerShell not found at its usual location.
  echo Tell me and we point this at whatever shell your machine has.
  pause
  exit /b 1
)

cd /d "%~dp0"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_audio_safety.ps1" %*

echo.
pause
