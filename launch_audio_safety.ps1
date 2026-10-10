# ══════════════════════════════════════════════════════════════════════
#  launch_audio_safety.ps1 - start the audio brain and open the dashboard
# ══════════════════════════════════════════════════════════════════════
# Called by "Open Audio Safety.bat".  Safe to double-click repeatedly: it
# reuses a brain that is already answering instead of stacking a second one.
#
#   -Port 5004   which port to serve on (SaferRide expects 5004)
#   -NoBrowser   start the brain but do not open a window (used for testing)

param(
    [int]    $Port      = 5004,
    [switch] $NoBrowser
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
# 127.0.0.1, not "localhost": this server binds IPv4 only, and a browser that
# tries the IPv6 name first can show an empty tab.  The address is printed in
# large text below regardless, so a blocked browser can never strand you.
$url  = "http://127.0.0.1:$Port"

Write-Host ""
Write-Host "  AUDIO SAFETY AI - starting" -ForegroundColor Cyan
Write-Host "  folder : $root"
Write-Host "  address: $url"
Write-Host ""

function Test-Brain {
    # True only if the brain answers a real page request.  A socket that merely
    # accepts connections is not enough - a wedged process does that.
    try {
        $r = Invoke-WebRequest -Uri "$url/" -UseBasicParsing -TimeoutSec 4
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Open-Dashboard {
    # Opening a browser is the one step that can fail quietly (no default
    # browser set, association broken, window hidden behind others).  Try the
    # normal way, then the shell's own "start" command, and always leave the
    # address on screen so it can be typed by hand.
    try {
        Start-Process $url -ErrorAction Stop
    } catch {
        try {
            & "$env:SystemRoot\System32\cmd.exe" /c start "" $url 2>$null
        } catch { }
    }
    Write-Host ""
    Write-Host "  ==============================" -ForegroundColor Green
    Write-Host "   OPEN THIS IN YOUR BROWSER:    $url" -ForegroundColor Yellow
    Write-Host "  ==============================" -ForegroundColor Green
    Write-Host "   Nothing appeared? Open your browser yourself and type that"
    Write-Host "   address. The brain is already running behind this window."
    Write-Host "   The FIRST chunk takes about 25 s (the AI model loads), and"
    Write-Host "   after that each one is fast - a still dial for half a minute"
    Write-Host "   after pressing Monitor is normal, not a hang."
    Write-Host ""
}

# ── 1. Something already answering? ───────────────────────────────────────
if (Test-Brain) {
    Write-Host "  A brain is already answering on $Port - opening it." -ForegroundColor Green
    Write-Host "  (if the dial never moves, that one is stale: close its"
    Write-Host "   window and double-click this again)"
    if (-not $NoBrowser) { Open-Dashboard }
    return
}

# ── 2. Port held by a process that does NOT answer = wedged. Clear it. ────
# This is the failure that costs real time: an old brain keeps the port, the
# browser loads its page happily, and every audio chunk silently never
# returns.  Only a browser tab would look fine.
$conns   = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$badPids = @($conns | ForEach-Object { $_.OwningProcess } | Where-Object { $_ -gt 0 } | Sort-Object -Unique)
foreach ($pid_ in $badPids) {
    $procName = (Get-Process -Id $pid_ -ErrorAction SilentlyContinue).ProcessName
    Write-Host "  clearing port ${Port}: PID $pid_ ($procName) holds it but answers nothing" -ForegroundColor Yellow
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
}
if ($badPids.Count -gt 0) { Start-Sleep -Seconds 2 }

# ── 3. Start the brain in its own window ──────────────────────────────────
# A visible console on purpose: it prints "[Keywords] Loaded 160 distress
# phrases" at boot and a line per chunk, so you can tell a dead pipeline from
# a quiet ride instead of guessing.  Closing that window stops the brain.
$env:PYTHONIOENCODING = "utf-8"
$env:AUDIO_SAFETY_PORT = "$Port"

$py = $null
# Resolved by absolute path first, because this machine's PATH has lost its
# Windows system folders - a bare "python" can fail for reasons that have
# nothing to do with the app.
$candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"
)
try { $candidates += (Get-Command python -ErrorAction Stop).Source } catch { }
try { $candidates += (Get-Command py -ErrorAction Stop).Source } catch { }
foreach ($c in $candidates) {
    if ($c -and (Test-Path $c)) { $py = $c; break }
}
if (-not $py) {
    Write-Host "  ERROR: could not find Python. Looked in:" -ForegroundColor Red
    $candidates | ForEach-Object { Write-Host "    $_" }
    Write-Host "  Nothing about the app itself is broken - tell me and we fix this."
    Read-Host "Press Enter to close"
    return
}
Write-Host "  python: $py"

Start-Process -FilePath $py -ArgumentList "server.py" -WorkingDirectory $root -WindowStyle Normal
Write-Host "  starting server.py ..." -NoNewline

# ── 4. Wait until it truly answers, then open the dashboard ───────────────
# The first chunk is slow (about half a minute) because YAMNet loads lazily.
# The page itself answers as soon as Flask is up.
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Brain) { $ok = $true; break }
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $ok) {
    Write-Host ""
    Write-Host "  STILL NOT ANSWERING after 80 s. Read the server window:" -ForegroundColor Red
    Write-Host "   - a Python error in red   -> the code is broken, tell me what it says"
    Write-Host "   - 'YAMNet ready' but no page -> port $Port is held by something else"
    Write-Host "   - a 'pkg_resources' warning is normal, ignore it"
    Write-Host ""
    Write-Host "   Meanwhile the address to try by hand is: $url" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    return
}

Write-Host ""
Write-Host "  READY" -ForegroundColor Green
Write-Host "  Monitor -> allow the microphone -> chunk #1 takes ~25 s (model loads),"
Write-Host "  after that it is fast. Each chunk now prints its peak, energy and"
Write-Host "  whether a distress word was matched."
Write-Host ""
if (-not $NoBrowser) { Open-Dashboard }
