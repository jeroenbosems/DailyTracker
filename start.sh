#!/usr/bin/env bash
# One action: spin up Daily Tracker in Docker.
exec "$(cd "$(dirname "$0")" && pwd)/scripts/start.sh"
