#!/usr/bin/env bash
# Daily Tracker one-command start (v0.5.1)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed (or not on PATH). Install Docker Desktop / Engine, then re-run ./scripts/start.sh" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is installed but not running. Start Docker, then re-run ./scripts/start.sh" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Error: neither 'docker compose' nor 'docker-compose' is available." >&2
  exit 1
fi

"${COMPOSE[@]}" up --build -d
echo "Daily Tracker is starting. Open http://localhost:8000"
