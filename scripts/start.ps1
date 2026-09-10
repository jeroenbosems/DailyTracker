# Daily Tracker — one-command Docker start
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root

function Fail([string]$msg) {
  Write-Error $msg
  exit 1
}

Write-Host "Daily Tracker — starting with Docker…"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Fail "Docker is not installed (or not on PATH). Install Docker Desktop, then run .\start.ps1"
}

try {
  docker info 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "not running" }
} catch {
  Fail "Docker is installed but not running. Start Docker Desktop, then run .\start.ps1"
}

Write-Host "Building and starting container (first run may take a minute)…"
docker compose version 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
  docker compose up --build -d
} elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
  docker-compose up --build -d
} else {
  Fail "neither 'docker compose' nor 'docker-compose' is available."
}

Write-Host "Waiting for http://localhost:8000 …"
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/login" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { $ready = $true; break }
  } catch { Start-Sleep -Seconds 1 }
}
docker compose ps 2>$null
Write-Host ""
if ($ready) {
  Write-Host "Ready. Open http://localhost:8000"
} else {
  Write-Host "Container is up (or still starting). Open http://localhost:8000"
}
Write-Host "Stop later with: docker compose down"
