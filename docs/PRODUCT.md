# Daily Tracker — Product pack v1

Source of truth for product decisions. Implementation lives in this repo and ships via Docker Compose.

## Vision

Solo task + routine tracker that feels like Guild Wars 2 achievements: clear progress, a next step always visible, and **standardized rewards** that pull you toward *needed* work (not DIY points or vanity busywork). Runs only as code in `jeroenbosems/DailyTracker` — clone, `docker compose up --build`, use.

## User

One local solo user (first-run setup creates the only account). No teams, no cloud identity, nothing tied to a personal/public identity in the product.

## Core objects

### Task (v0.1)

One-off work item.

| Field | Notes |
|-------|--------|
| title | required |
| notes | optional |
| priority | 1–3 (1 = must-do / needed) |
| due date | optional |
| completed | flag + timestamp |

### Routine (v0.1)

Recurring work.

- Cadence: `daily` \| `weekly` \| `monthly` \| `yearly`
- Same priority model as tasks
- Tracks: streak, best streak, completion count, last completed, next due

### Reward (v0.1)

Fixed tiers only (never user-defined points):

| Tier | Priority | Points |
|------|----------|--------|
| Gold | 1 | 50 |
| Silver | 2 | 25 |
| Bronze | 3 | 10 |

Completing a task or routine grants that tier. Every grant is logged; UI shows total points.

### Goal / Achievement (v0.2)

Big target broken into ordered steps (GW2-style). Progress = steps done / total; UI always shows the *next* incomplete step. Completing a step can auto-complete or link a task/routine. Fixed reward on goal completion (Gold). **Not in v0.1.**

## Today / Due-now (product rules)

- **Surface:** overdue items, due today, and routines whose `next_due ≤ today`.
- **Do not** put undated open tasks in Due-now (they stay under Open tasks).
- **Sort:** priority ascending (1 first), then due date ascending, then created.
- Needed work beats fun busywork: priority 1 always above 2/3 even if 2/3 are older.
- Completing a routine advances `next_due` by cadence and updates streak (break streak if a full period was missed).

## UX flows (v0.1 must support)

Setup → Login → Today board → Create task/routine → Complete from Today → See reward feedback + streak/points → Logout.

Graceful error pages (no raw stacks). Data persists in a named Docker volume.

## Explicit non-goals

Multi-user, cloud sync, mobile apps, OAuth/IdP, custom reward economies, integrations (Jira/Trello/etc.), telemetry.

## NFR bar

- Local auth (argon2 preferred / bcrypt acceptable)
- Session cookies: HttpOnly + SameSite=Lax (+ Secure if TLS)
- All data in the container volume
- No secrets in repo
- No outbound telemetry/PII by default
- Graceful errors; fine for single-user solo use

## Sequence

| Version | Scope |
|---------|--------|
| **v0.1** | Auth + tasks + routines + today/due-now + fixed rewards/streaks + Docker |
| **v0.2** | Goals/achievements with ordered steps + next-step surfacing on Today |
| **v0.3** | Reward history view, edit/delete polish, empty states, light “why this is due now” copy |

Product decisions land with the Product Owner.
