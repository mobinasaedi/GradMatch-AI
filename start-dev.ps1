<#
    GradMatch AI - one-command local start (Windows PowerShell)

        .\start-dev.ps1              start the API + web app and open the browser
        .\start-dev.ps1 -Setup       install Python/Node dependencies first
        .\start-dev.ps1 -NoBrowser   do not open the browser

    ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less UTF-8 files as ANSI.
#>
param(
    [switch]$Setup,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

function Write-Step($message) { Write-Host "  $message" -ForegroundColor Cyan }
function Write-Ok($message) { Write-Host "  OK  $message" -ForegroundColor Green }

function Test-Http($url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "  GradMatch AI" -ForegroundColor White -NoNewline
Write-Host " | local demo" -ForegroundColor DarkGray
Write-Host "  ----------------------------------------"

if (-not (Test-Path $python)) { $Setup = $true }

if ($Setup) {
    Write-Step 'Creating the Python virtual environment...'
    Push-Location $backend
    python -m venv .venv
    & $python -m pip install --upgrade pip --quiet
    & $python -m pip install -r requirements.txt --quiet
    Pop-Location

    $envFile = Join-Path $backend '.env'
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $root '.env.example') $envFile
        $secret = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
        (Get-Content $envFile) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" | Set-Content $envFile
        Write-Ok 'backend\.env created with a fresh SECRET_KEY'
    }

    if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
        Write-Step 'Installing frontend dependencies...'
        Push-Location $frontend
        npm install --no-audit --no-fund
        Pop-Location
    }
    Write-Ok 'dependencies installed'
}

# --- API -------------------------------------------------------------------
if (Test-Http 'http://127.0.0.1:8000/api/health') {
    Write-Step 'Backend already running on port 8000.'
} else {
    Write-Step 'Starting the FastAPI backend on http://127.0.0.1:8000'
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory $backend | Out-Null
}

# --- web -------------------------------------------------------------------
if (Test-Http 'http://127.0.0.1:5173/') {
    Write-Step 'Web app already running on port 5173.'
} else {
    Write-Step 'Starting the Vite dev server on http://127.0.0.1:5173'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' -WorkingDirectory $frontend | Out-Null
}

# --- wait for the API to answer -------------------------------------------
$health = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
        break
    } catch { }
}

if ($health) {
    $mode = 'bundled dataset (no key needed)'
    if ($health.openalex_key_configured) { $mode = 'live OpenAlex' }
    Write-Ok ("API online | v{0} | {1} professors | {2}" -f $health.version, $health.professors_indexed, $mode)
} else {
    Write-Host '  The API did not answer on port 8000 - check the backend window for errors.' -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  App:          http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  API docs:     http://127.0.0.1:8000/docs" -ForegroundColor DarkGray
Write-Host "  Demo account: demo@gradmatch.ai / gradmatch-demo-2026" -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser -and $health) { Start-Process 'http://127.0.0.1:5173' }
