# 850 SCOS — One-click auto-start install
# Usage: powershell -ExecutionPolicy Bypass -File setup-startup.ps1 -Engine|-Portal
param([switch]$Engine, [switch]$Portal)

$startup = [Environment]::GetFolderPath('Startup')
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Install-VBS($name, $vbsDir) {
    $src = Join-Path $scriptDir $vbsDir "start-silent.vbs"
    $dst = Join-Path $startup "$name.vbs"
    if (Test-Path $dst) { Remove-Item $dst -Force }
    Copy-Item $src $dst -Force
    Write-Host "Installed: $dst"
}

if ($Engine) {
    Install-VBS "850-SCOS-Engine" "data-engine"
    Write-Host "Company PC: Engine auto-starts on boot (silent)"
} elseif ($Portal) {
    Install-VBS "850-SCOS-Portal" "portal"
    Write-Host "Yumin PC: Portal auto-starts on boot (silent)"
} else {
    Write-Host "Usage: setup-startup.ps1 -Engine  (Company computer)"
    Write-Host "       setup-startup.ps1 -Portal (Yumin computer)"
}
