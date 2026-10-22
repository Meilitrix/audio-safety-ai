# Generates square app icons from the wide Abhi AI logo lockup.
# The logo is 554x339 with a transparent background; the mark itself occupies
# x=18..540, y=20..322. Browser tabs and iOS home screens want a SQUARE image,
# so we crop to the mark and letterbox it into a square canvas at high quality.
Add-Type -AssemblyName System.Drawing

$src = "C:\Users\user\Documents\Qoder\2026-09-14\chat-1\saferide-ai\public\logo.png"
$outDir = "d:\audio-safety-ai-1\_merge\public"

$script:bmp = New-Object System.Drawing.Bitmap $src
# Full lockup (mark + speed lines) - used only where a wide logo is fine.
$script:sx = 18; $script:sy = 20; $script:sw = 523; $script:sh = 303
# Square-ish crop of the "A" glyph alone (including its left leg, which reaches
# further left at the bottom): icons must be square, and the glyph is what stays
# legible at 16px in a browser tab. Speed lines are intentionally excluded.
$script:qx = 133; $script:qy = 18; $script:qw = 410; $script:qh = 306

function New-SquareIcon {
    param([int]$size, [switch]$opaque, [string]$path, [double]$padRatio)
    $canvas = New-Object System.Drawing.Bitmap $size, $size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($canvas)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    if ($opaque) { $g.Clear([System.Drawing.Color]::White) } else { $g.Clear([System.Drawing.Color]::Transparent) }

    $pad = [int][math]::Round($size * $padRatio)
    $avail = $size - (2 * $pad)
    $cw = $script:qw; $ch = $script:qh; $cx = $script:qx; $cy = $script:qy
    $scale = [math]::Min($avail / $cw, $avail / $ch)
    $dw = [int][math]::Round($cw * $scale)
    $dh = [int][math]::Round($ch * $scale)
    $dx = [int](($size - $dw) / 2)
    $dy = [int](($size - $dh) / 2)

    $destRect = New-Object System.Drawing.Rectangle $dx, $dy, $dw, $dh
    $srcRect = New-Object System.Drawing.Rectangle $cx, $cy, $cw, $ch
    [void]$g.DrawImage($script:bmp, $destRect, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    $canvas.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $canvas.Dispose()
    Write-Output "wrote $path ($size x $size, mark ${dw}x${dh})"
}

New-SquareIcon -size 64 -path (Join-Path $outDir "favicon.png") -padRatio 0.04
New-SquareIcon -size 180 -opaque -path (Join-Path $outDir "apple-touch-icon.png") -padRatio 0.08
New-SquareIcon -size 512 -path (Join-Path $outDir "site-icon.png") -padRatio 0.08

$script:bmp.Dispose()
