param(
    [ValidateSet('dev', 'start')]
    [string]$Mode = 'dev',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPath = Join-Path $ProjectRoot 'backend'
$FrontendPath = Join-Path $ProjectRoot 'frontend'
$PythonPath = Join-Path $ProjectRoot '.venv311\Scripts\python.exe'

if (-not (Test-Path $PythonPath)) {
    throw "Missing Python interpreter at $PythonPath. Create .venv311 first."
}

function Start-ServiceTerminal {
    param(
        [string]$Title,
        [string]$Command,
        [switch]$DryRun
    )

    if ($DryRun) {
        Write-Host "[$Title] $Command"
        return
    }

    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-Command',
        "$host.UI.RawUI.WindowTitle = '$Title'; $Command"
    ) | Out-Null
}

$ttsCommand = "Set-Location `"$ProjectRoot`"; & `"$PythonPath`" -m uvicorn backend.tts_fastapi.app:app --host 127.0.0.1 --port 8001"

if ($Mode -eq 'dev') {
    $backendCommand = "Set-Location `"$BackendPath`"; npm run dev"
    $frontendCommand = "Set-Location `"$FrontendPath`"; npm run dev -- --host 127.0.0.1 --port 5173"
}
else {
    $backendCommand = "Set-Location `"$BackendPath`"; npm run start"
    $frontendCommand = "Set-Location `"$FrontendPath`"; npm run build; npm run preview -- --host 127.0.0.1 --port 4173"
}

Start-ServiceTerminal -Title 'TTS FastAPI' -Command $ttsCommand -DryRun:$DryRun
Start-ServiceTerminal -Title "Backend ($Mode)" -Command $backendCommand -DryRun:$DryRun
Start-ServiceTerminal -Title "Frontend ($Mode)" -Command $frontendCommand -DryRun:$DryRun

Write-Host "Quickstart mode: $Mode"
if ($Mode -eq 'dev') {
    Write-Host 'Frontend URL: http://127.0.0.1:5173'
}
else {
    Write-Host 'Frontend URL: http://127.0.0.1:4173'
}
Write-Host 'TTS health: http://127.0.0.1:8001/health'
Write-Host 'Backend TTS health: http://127.0.0.1:5000/api/tts/health'
Write-Host 'Use Ctrl+C in each terminal to stop services.'
