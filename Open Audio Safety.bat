@echo off
rem ══════════════════════════════════════════════════════════════════════
rem  Open Audio Safety.bat  -  double-click to start the brain and open the
rem  dashboard.  Kept tiny on purpose: all the logic lives in the .ps1 next
rem  to it, so there is one place to fix and no duplicated behaviour.
rem ══════════════════════════════════════════════════════════════════════
title Audio Safety AI
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_audio_safety.ps1"
echo.
pause
