# Installs Cursor Resize & Opacity into Krita (Windows)
$ErrorActionPreference = "Stop"

$kritaDir   = Join-Path $env:APPDATA "krita"
$pykritaDir = Join-Path $kritaDir "pykrita"
$actionsDir = Join-Path $kritaDir "actions"
New-Item -ItemType Directory -Path $pykritaDir -Force | Out-Null
New-Item -ItemType Directory -Path $actionsDir -Force | Out-Null

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item -Path (Join-Path $scriptDir "cursor_resize_opacity.desktop") -Destination $pykritaDir -Force
Copy-Item -Path (Join-Path $scriptDir "cursor_resize_opacity") -Destination $pykritaDir -Recurse -Force
Copy-Item -Path (Join-Path $scriptDir "cursor_resize_opacity\cursor_resize_opacity.action") -Destination $actionsDir -Force

Write-Host "Installed to $pykritaDir" -ForegroundColor Green
Write-Host "1. Restart Krita."
Write-Host "2. Settings > Configure Krita > Python Plugin Manager > enable 'Cursor Resize & Opacity'."
Write-Host "3. Restart Krita again, then hold Alt over the canvas and move the cursor."
