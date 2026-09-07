# Daily Tracker

Solo local task + routine tracker (daily / weekly / monthly / yearly) with GW2-style progress feedback: clear next step, streaks, and **fixed standardized rewards** (not DIY points).

Designed to run everywhere via Docker. One user, data on a named volume, no cloud identity, no outbound telemetry by default.

## Quick start

```bash
docker compose up --build
```

Open http://localhost:8000

1. First visit creates your **local** account (username + password).
2. Add tasks and routines.
3. Use **Due now** to see overdue / due-today work, ordered by priority (needed work first).
4. Completing items grants Bronze / Silver / Gold rewards (10 / 25 / 50 pts by priority).

## Stack

- FastAPI + Jinja2 thin UI (same image)
- SQLite on Docker volume `dailytracker_data` → `/data`
- Local session cookies (`HttpOnly`, `SameSite=Lax`; set `SECURE_COOKIES=true` behind TLS)
- Password hashing: **argon2**

## Configuration

| Env | Meaning |
|-----|---------|
| `DATA_DIR` | SQLite + session secret dir (default `/data`) |
| `SESSION_SECRET` | Optional; otherwise generated once into `$DATA_DIR/.session_secret` |
| `SECURE_COOKIES` | Set `true` when serving over HTTPS |

No secrets are committed to the repo.

## Security notes

- Local auth only — no cloud IdP / personal identity hooks
- App data stays in the container volume
- No outbound calls / telemetry by default
- UI shows graceful errors (no raw stack traces)
- Do not publish this service to the public internet without TLS and hardened reverse-proxy settings

## Develop / test locally (optional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATA_DIR=./data uvicorn app.main:app --reload
pytest
```

## License

See `LICENSE`.
