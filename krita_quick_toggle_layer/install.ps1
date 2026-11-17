# PowerShell script to install Quick Toggle Layer into Krita
$ErrorActionPreference = "Stop"

$kritaDir = Join-Path $env:APPDATA "krita"
$pykritaDir = Join-Path $kritaDir "pykrita"
$actionsDir = Join-Path $kritaDir "actions"

Write-Host "Checking Krita directories..." -ForegroundColor Cyan

if (-not (Test-Path $pykritaDir)) {
    New-Item -ItemType Directory -Path $pykritaDir -Force | Out-Null
}

if (-not (Test-Path $actionsDir)) {
    New-Item -ItemType Directory -Path $actionsDir -Force | Out-Null
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDesktop = Join-Path $scriptDir "quick_toggle_layer.desktop"
$sourcePackage = Join-Path $scriptDir "quick_toggle_layer"
$sourceAction  = Join-Path $scriptDir "quick_toggle_layer\quick_toggle_layer.action"

Write-Host "Copying plugin files to: $pykritaDir" -ForegroundColor Green
Copy-Item -Path $sourceDesktop -Destination $pykritaDir -Force
Copy-Item -Path $sourcePackage -Destination $pykritaDir -Recurse -Force

if (Test-Path $sourceAction) {
    Write-Host "Copying action definition to: $actionsDir" -ForegroundColor Green
    Copy-Item -Path $sourceAction -Destination $actionsDir -Force
}

Write-Host "`nInstallation successful!" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "1. Open or Restart Krita (5.x)."
Write-Host "2. Go to: Settings -> Configure Krita -> Python Plugin Manager."
Write-Host "3. Check the box next to 'Quick Toggle Layer' and click OK."
Write-Host "4. Restart Krita once more."
Write-Host "5. Go to: Settings -> Configure Shortcuts -> search for 'Quick Toggle' and assign your favorite hotkey (e.g. F2 or Shift+V)!"
