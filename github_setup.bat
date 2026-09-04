@echo off
echo ============================================
echo   GitHub Setup - Audio Safety AI
echo ============================================
echo.

REM Refresh PATH
set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI"

REM Check if logged in
"C:\Program Files\GitHub CLI\gh.exe" auth status >nul 2>&1
if errorlevel 1 (
    echo ERROR: You are not logged into GitHub.
    echo Please run github_login.bat first!
    pause
    exit /b 1
)

echo [OK] GitHub login confirmed.
echo.

REM Go to project folder
cd /d "c:\Users\user\Documents\Qoder\2026-09-03\chat-1\audio_safety_ai"

REM Initialize Git
if not exist ".git" (
    echo [1/5] Initializing Git repository...
    git init
) else (
    echo [1/5] Git already initialized, skipping.
)

REM Set default branch
git branch -M main 2>nul

REM Add all files
echo [2/5] Adding project files...
git add .

REM Commit
echo [3/5] Creating commit...
git commit -m "Audio Safety AI: YAMNet + Web Speech API - ride-sharing safety monitor" >nul 2>&1
if errorlevel 1 (
    echo [3/5] No new changes to commit.
) else (
    echo [3/5] Commit created.
)

REM Get GitHub username
for /f "tokens=*" %%i in ('"C:\Program Files\GitHub CLI\gh.exe" api user --jq .login 2^>nul') do set GH_USER=%%i
echo.
echo Your GitHub username: %GH_USER%
echo.

REM Create repo on GitHub
echo [4/5] Creating GitHub repository...
"C:\Program Files\GitHub CLI\gh.exe" repo create audio-safety-ai --public --description "AI-powered ride-sharing safety monitor using YAMNet audio classification and Web Speech API transcription" --source=. --push --yes

if errorlevel 1 (
    echo.
    echo [4/5] Repo might already exist. Trying to push anyway...
    git remote set-url origin https://github.com/%GH_USER%/audio-safety-ai.git
    git push -u origin main
)

echo.
echo ============================================
echo   DONE! Your project is on GitHub:
echo   https://github.com/%GH_USER%/audio-safety-ai
echo ============================================
echo.
pause
