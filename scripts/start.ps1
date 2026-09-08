# Daily Tracker one-command start (v0.5.1)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root

function Fail([string]$msg) {
  Write-Error $msg
  exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Fail "Docker is not installed (or not on PATH). Install Docker Desktop, then re-run scripts/start.ps1"
}

try {
  docker info 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "not running" }
} catch {
  Fail "Docker is installed but not running. Start Docker Desktop, then re-run scripts/start.ps1"
}

$composeOk = $false
docker compose version 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
  docker compose up --build -d
  $composeOk = $true
} elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
  docker-compose up --build -d
  $composeOk = $true
}

if (-not $composeOk) {
  Fail "neither 'docker compose' nor 'docker-compose' is available."
}

Write-Host "Daily Tracker is starting. Open http://localhost:8000"
