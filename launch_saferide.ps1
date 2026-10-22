# ══════════════════════════════════════════════════════════════════════
#  launch_saferide.ps1 - start the ride app (and the brain it listens to)
# ══════════════════════════════════════════════════════════════════════
# Called by "Open SaferRide.bat".  Double-clicking it twice is safe: a brain or
# a ride app that is already answering gets reused instead of stacked.
#
#   -Port       5008  which port the ride app serves on (hardcoded in server.ts)
#   -BrainPort  5004  where SaferRide expects the audio brain
#   -NoBrowser  start things but do not open a browser window
#
# Everything external is resolved by ABSOLUTE PATH.  This machine's PATH has
# lost its Windows system folders, so a bare "powershell", "node" or "npm" can
# fail for reasons that have nothing to do with the app.

param(
    [int]    $Port      = 5008,
    [int]    $BrainPort = 5004,
    [switch] $NoBrowser
)

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$url     = "http://127.0.0.1:$Port"
$brainUrl = "http://127.0.0.1:$BrainPort"

# Where the ride app lives.  Resolved from a list of candidates so the same
# launcher works on any laptop after a clone, not just this one.  The first
# candidate that actually contains package.json wins.  Add or reorder entries
# here if the project layout changes - nothing else in this file needs to know.
$appCandidates = @(
    (Join-Path $root "..\saferide-ai"),                         # combined repo: brain folder's sibling
    (Join-Path $root "saferide-ai"),                            # combined repo: ride app nested here
    "C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai"  # this machine's development copy
)
$appDir = $appCandidates | Where-Object { Test-Path (Join-Path $_ "package.json") } | Select-Object -First 1
if (-not $appDir) { $appDir = $appCandidates[0] }   # sensible thing to print in the error below

Write-Host ""
Write-Host "  SAFERIDE - starting" -ForegroundColor Cyan
Write-Host "  folder : $appDir"
Write-Host "  address: $url"
Write-Host ""

function Test-Answer($target, $secs = 4) {
    # A port that merely accepts a socket is not "up" - a starved process does
    # that too.  Ask for a real page and check the status.
    try {
        $r = Invoke-WebRequest -Uri "$target/" -UseBasicParsing -TimeoutSec $secs
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Open-Page($target, $what) {
    # Opening a browser is the step that fails quietly (no default browser,
    # broken association, window behind others).  Try twice, then leave the
    # address in large text so it can always be typed by hand.
    try { Start-Process $target -ErrorAction Stop }
    catch {
        try { & "$env:SystemRoot\System32\cmd.exe" /c start "" $target 2>$null } catch { }
    }
    Write-Host ""
    Write-Host "  ==============================" -ForegroundColor Green
    Write-Host   "   OPEN THIS IN YOUR BROWSER:    $target" -ForegroundColor Yellow
    Write-Host "  ==============================" -ForegroundColor Green
    Write-Host   "   ($what)"
    Write-Host ""
}

if (-not (Test-Path "$appDir\package.json")) {
    Write-Host "  ERROR: no SaferRide found in any expected folder:" -ForegroundColor Red
    foreach ($c in $appCandidates) { Write-Host "    tried: $c" }
    Write-Host "  The app is not broken, it just is not cloned next to this"
    Write-Host "  launcher. Put the saferide-ai folder beside this one (as a"
    Write-Host "  sibling), or add its path to \$appCandidates at the top."
    Read-Host "Press Enter to close"
    return
}

# ── 1. The brain first, because the dial has no other source ─────────────
# Reuse the audio launcher wholesale rather than copying its logic: it already
# knows how to wait for a brain that is still loading its model, and how to
# clear a port held by one that answers nothing.
if (Test-Answer $brainUrl) {
    Write-Host "  audio brain already answering on $BrainPort" -ForegroundColor Green
} else {
    Write-Host "  brain not answering - starting it through launch_audio_safety.ps1" -ForegroundColor Yellow
    Write-Host "  (its own black window will appear; the first audio chunk also"
    Write-Host "   takes ~25 s while YAMNet loads - that is normal)"
    & "$root\launch_audio_safety.ps1" -Port $BrainPort -NoBrowser
}

# ── 2. Is the ride app already running? ──────────────────────────────────
if (Test-Answer $url) {
    Write-Host "  SaferRide already answering on $Port - opening it." -ForegroundColor Green
    if (-not $NoBrowser) { Open-Page $url "SaferRide" }
    return
}

# Same double-click-too-soon guard as the brain: Vite takes a few seconds to
# come up, and a second dev server on the same port just fails.
$holding = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($holding.Count -gt 0) {
    Write-Host "  something already holds port $Port - waiting for it to wake up" -ForegroundColor Yellow
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        if (Test-Answer $url) {
            Write-Host ""
            Write-Host "  it is answering - opening it." -ForegroundColor Green
            if (-not $NoBrowser) { Open-Page $url "SaferRide" }
            return
        }
        Write-Host "." -NoNewline
    }
    Write-Host ""
    Write-Host "  it holds the port but answered nothing in 60 s." -ForegroundColor Yellow
    Write-Host "  If this laptop is short on RAM (it has 4 GB), close some"
    Write-Host "  browser tabs or the Qoder window - Windows then squeezes the"
    Write-Host "  servers so small they cannot make progress." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    return
}

# ── 3. Start the dev server in its own visible window ────────────────────
# Visible on purpose: a red error in server.ts is readable there, and /k keeps
# the window open after a crash instead of vanishing.
$np = $null
foreach ($c in @("C:\Program Files\nodejs", "C:\Program Files (x86)\nodejs")) {
    if (Test-Path "$c\npm.cmd") { $np = $c; break }
}
try { if (-not $np) { $np = Split-Path (Get-Command npm -ErrorAction Stop).Source } } catch { }
if (-not $np) {
    Write-Host "  ERROR: could not find npm. Looked in:" -ForegroundColor Red
    Write-Host "    C:\Program Files\nodejs\npm.cmd"
    Write-Host "  Nothing about the app itself is broken - tell me and we fix this."
    Read-Host "Press Enter to close"
    return
}
Write-Host "  npm folder: $np"

$inner = "title SaferRide dev server && cd /d `"$appDir`" && `"$np\npm.cmd`" run dev"
Start-Process -FilePath "$env:SystemRoot\System32\cmd.exe" -ArgumentList "/k", $inner -WindowStyle Normal
Write-Host "  starting npm run dev ..." -NoNewline

# ── 4. Wait until it truly answers, then open it ─────────────────────────
$ok = $false
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Answer $url 3) { $ok = $true; break }
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $ok) {
    Write-Host ""
    Write-Host "  STILL NOT ANSWERING after 90 s. Read the SaferRide window:" -ForegroundColor Red
    Write-Host "   - red text mentioning an import or 'Error'  -> tell me what it says"
    Write-Host "   - 'Abhi AI server listening on ...:5008'     -> it IS up, use the address below"
    Write-Host "   - nothing printed for a long time            -> RAM: close browser tabs, retry"
    Write-Host ""
    Write-Host "   Meanwhile the address to try by hand is: $url" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    return
}

Write-Host ""
Write-Host "  READY - brain on $BrainPort, ride app on $Port" -ForegroundColor Green
Write-Host "  Book a ride -> start the trip -> allow the microphone."
Write-Host "  The map tiles come from the internet; with no connection the map"
Write-Host "  area is grey but the dial, the trip and SOS all still work."
Write-Host ""
if (-not $NoBrowser) { Open-Page $url "SaferRide" }
