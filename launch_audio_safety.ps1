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
$url  = "http://localhost:$Port"

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

# ── 1. Something already answering? ───────────────────────────────────────
if (Test-Brain) {
    Write-Host "  A brain is already answering on $Port - opening it." -ForegroundColor Green
    Write-Host "  (if the dial never moves, that one is stale: close its"
    Write-Host "   window and double-click this again)"
    if (-not $NoBrowser) { Start-Process $url }
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

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Host "  ERROR: python is not on PATH - cannot start the brain." -ForegroundColor Red
    Write-Host "  Tell me and we fix the PATH; nothing else about the app is broken."
    pause
    return
}

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
    pause
    return
}

Write-Host ""
Write-Host "  READY  ->  $url" -ForegroundColor Green
Write-Host "  Monitor -> allow the microphone -> chunk #1 takes ~30 s (model loads),"
Write-Host "  after that it is fast. Each chunk now prints its peak, energy and"
Write-Host "  whether a distress word was matched."
Write-Host ""
if (-not $NoBrowser) { Start-Process $url }
