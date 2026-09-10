#!/usr/bin/env bash
# Daily Tracker — one-command Docker start
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Daily Tracker — starting with Docker…"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed (or not on PATH)." >&2
  echo "Mac: install Docker Desktop for Mac, open it, then run: ./start.sh" >&2
  echo "Linux: install Docker Engine (or Desktop), then run: ./start.sh" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is installed but not running." >&2
  echo "Mac: open Docker Desktop and wait until it is ready, then run: ./start.sh" >&2
  echo "Linux: start the Docker daemon, then run: ./start.sh" >&2
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

echo "Building and starting container (first run may take a minute)…"
"${COMPOSE[@]}" up --build -d

echo "Waiting for http://localhost:8000 …"
ready=0
for i in $(seq 1 60); do
  if curl -sf -o /dev/null http://127.0.0.1:8000/login 2>/dev/null \
    || curl -sf -o /dev/null http://127.0.0.1:8000/ 2>/dev/null; then
    ready=1
    break
  fi
  # fallback: container running even if curl missing
  if ! command -v curl >/dev/null 2>&1; then
    if "${COMPOSE[@]}" ps --status running 2>/dev/null | grep -q dailytracker; then
      sleep 2
      ready=1
      break
    fi
  fi
  sleep 1
done

"${COMPOSE[@]}" ps || true
echo ""
if [[ "$ready" -eq 1 ]]; then
  echo "Ready. Open http://localhost:8000"
else
  echo "Container is up (or still starting). Open http://localhost:8000"
  echo "If the page does not load, run: docker compose logs -f"
fi
echo "Stop later with: ./scripts/stop.sh   (or: docker compose down)"
