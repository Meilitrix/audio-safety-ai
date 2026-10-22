# ══════════════════════════════════════════════════════════════════════
#  make_desktop_shortcuts.ps1 - recreate the two desktop icons
# ══════════════════════════════════════════════════════════════════════
# Run this ONCE on any machine after cloning. It builds "Open SaferRide" and
# "Open Audio Safety" shortcuts on the current user's Desktop, pointing at the
# .bat files that sit NEXT TO THIS SCRIPT - so the icons are correct no matter
# which folder or drive you cloned into. A committed .lnk cannot do this: a
# Windows shortcut has one absolute path baked in and breaks the moment the
# repo lives anywhere else.
#
#   Double-click it, or:  powershell -ExecutionPolicy Bypass -File .\make_desktop_shortcuts.ps1

$ErrorActionPreference = "Stop"
$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")

$targets = @(
    @{ name = "Open SaferRide";    bat = "Open SaferRide.bat";    icon = "$env:SystemRoot\System32\shell32.dll,13" },
    @{ name = "Open Audio Safety"; bat = "Open Audio Safety.bat"; icon = "$env:SystemRoot\System32\shell32.dll,13" }
)

$shell = New-Object -ComObject WScript.Shell
foreach ($t in $targets) {
    $bat = Join-Path $root $t.bat
    if (-not (Test-Path $bat)) {
        Write-Host "  SKIP: '$($t.bat)' is not beside this script ($root)" -ForegroundColor Yellow
        continue
    }
    $lnkPath = Join-Path $desktop ($t.name + ".lnk")
    $sc = $shell.CreateShortcut($lnkPath)
    $sc.TargetPath       = $bat
    $sc.WorkingDirectory = $root
    $sc.IconLocation     = $t.icon
    $sc.Description      = "$($t.name) - Abhi AI launcher (created by make_desktop_shortcuts.ps1)"
    $sc.Save()
    Write-Host "  created: $lnkPath  ->  $bat" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Done. The two icons are on your Desktop ($desktop)." -ForegroundColor Cyan
Write-Host "  Double-click 'Open SaferRide' to start the brain + ride app together."
