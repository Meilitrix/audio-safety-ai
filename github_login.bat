@echo off
echo ============================================
echo   GitHub Login - Audio Safety AI
echo ============================================
echo.
echo This will open your browser to log into GitHub.
echo.
pause

"C:\Program Files\GitHub CLI\gh.exe" auth login --hostname github.com --git-protocol https --web

echo.
echo ============================================
echo   Checking login status...
echo ============================================
"C:\Program Files\GitHub CLI\gh.exe" auth status
echo.
echo If you see your username above, login worked!
echo You can close this window.
pause
