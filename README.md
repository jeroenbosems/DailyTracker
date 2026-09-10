# Daily Tracker

## Start here (one action)

**Mac / Linux** (Docker Desktop or Engine must be running):

```bash
./start.sh
```

**Windows:**

```powershell
.\start.ps1
```

That builds the image, starts the container, and prints **http://localhost:8000**. First visit creates your local account.

**Mac tip:** install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), open it, wait until the whale icon is idle, then run `./start.sh` from the repo root in Terminal (or VS Code).

- VS Code: Terminal → Run Build Task → **Start Daily Tracker (Docker)**
- Stop: `./scripts/stop.sh` or `docker compose down`

No env files, no manual `compose` commands needed for normal use.

---

Solo local task + routine tracker (daily / weekly / monthly / yearly) with clear next-step progress, soft streaks, and **fixed standardized rewards** (not DIY points). Hierarchy: **Epic → Phase → Step** plus Period bonuses.

Designed to run everywhere via Docker. One user, data on a named volume, no cloud identity, no outbound telemetry by default.

## Quick start

Same as **Start here** above:

```bash
./start.sh
```

## Shippable RC (`v1.0-rc`)

Stable, workable cut for real use. Feature freeze to **bugfixes only** after the `v1.0-rc` tag until `v1.0` or reopen.

**Run (only required path):**

```bash
./start.sh
```

Mac / Linux: `./start.sh` · Windows: `.\start.ps1`

Checks Docker, runs `compose up --build -d`, prints http://localhost:8000. Open in VS Code → run start script. No extra config.

**In this cut:** Epics → Phases → Steps, Park, Full/Focused, Follow-on, life modes, starter templates, LLM ingest, reward shop, export/backup, Watch/Nearly done, weekly review (`/review`), plus the start scripts above.

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

## Product requirements

Authoritative product docs live in [`docs/`](./docs/) — start with [`REQUIREMENTS.md`](./docs/REQUIREMENTS.md). Chat is not the spec.
