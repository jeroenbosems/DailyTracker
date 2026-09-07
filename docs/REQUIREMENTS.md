# Daily Tracker — Requirements

Normative. **MUST** / **SHOULD** / **MAY**.  
If this file conflicts with chat, **this file wins** after merge to `main`.

Version tags: `[v0.1]` shipped · `[v0.2]` shipped · `[v0.3]` shipped · `[v0.3.1]` shipped · `[v0.3.2]` in progress

---

## R1 — Delivery & runtime

| ID | Requirement | Ver |
|----|-------------|-----|
| R1.1 | MUST ship as code in `jeroenbosems/DailyTracker` runnable via Docker Compose | v0.1 |
| R1.2 | MUST persist data in a named Docker volume | v0.1 |
| R1.3 | MUST run as a single-user local app (no cloud IdP) | v0.1 |
| R1.4 | MUST NOT require secrets committed to the repo | v0.1 |
| R1.5 | MUST NOT send telemetry / PII outbound by default | v0.1 |

## R2 — Security & quality

| ID | Requirement | Ver |
|----|-------------|-----|
| R2.1 | MUST use local password auth with argon2 (or bcrypt) | v0.1 |
| R2.2 | MUST set session cookies HttpOnly + SameSite=Lax (+ Secure if TLS) | v0.1 |
| R2.3 | MUST show graceful errors (no raw stacks in UI) | v0.1 |
| R2.4 | SHOULD remain performant for single-user solo use | v0.1 |

## R3 — Tasks & Routines

| ID | Requirement | Ver |
|----|-------------|-----|
| R3.1 | MUST support Tasks: title, optional notes, priority 1–3, optional due date, complete | v0.1 |
| R3.2 | MUST support Routines: cadences daily/weekly/monthly/yearly, priority, streak + best streak, next due | v0.1 |
| R3.3 | MUST grant fixed Priority rewards on completion: Gold/pri1, Silver/pri2, Bronze/pri3 | v0.1 |
| R3.4 | MUST NOT allow user-defined point economies | v0.1 |

## R4 — Today & Due now

| ID | Requirement | Ver |
|----|-------------|-----|
| R4.1 | MUST surface Due now: overdue, due today, routines with next_due ≤ today | v0.1 |
| R4.2 | MUST NOT put undated open Tasks in Due now | v0.1 |
| R4.3 | MUST sort Due now by priority asc, then due date asc, then created | v0.1 |
| R4.4 | MUST prefer needed work (priority 1 / Active Epic Steps) over lower-value busywork | v0.1+ |
| R4.5 | SHOULD surface Watch / Nearly done on Today (max 6: pinned Steps/Tasks + auto nearly-done Steps), below Due now and Active Epic | v0.3.1 |
| R4.6 | MUST provide read-only RewardLog history (newest first) without DIY point economies | v0.3.1 |

## R5 — Epics, Phases, Steps

| ID | Requirement | Ver |
|----|-------------|-----|
| R5.1 | MUST model Epic → ordered Phase → ordered Step | v0.2 |
| R5.2 | MUST show next incomplete Step, % Phase, % Epic | v0.2 |
| R5.3 | MUST surface next Step for the Active Epic on Today | v0.2 |
| R5.4 | MUST allow optional parent Epic (meta) | v0.2 |
| R5.5 | SHOULD allow Step link to Task and/or Routine | v0.2 |
| R5.6 | MUST support parallel Steps within a Phase (any order) when marked parallel | v0.2 |
| R5.7 | MUST support Epic fields for end **identity** and **capability** (what unlocks in real life) | v0.2 |
| R5.8 | SHOULD support Phase **intermediate deliverable** description (real usable outcome) | v0.2 |
| R5.9 | SHOULD support Epic **preview** (early taste of end state) | v0.2 |
| R5.10 | MUST celebrate completions at Step < Phase < Epic scale (distinct feedback) | v0.2 |
| R5.11 | MUST allow exactly one Active Epic for Today focus | v0.2 |
| R5.12 | SHOULD support Parked Epics without punishing the user | v0.2 / polish v0.3 |
| R5.13 | SHOULD support Full vs Focused Epic paths; switches must not silently wipe progress | v0.3.2 |

## R6 — Soft miss & Period bonuses

| ID | Requirement | Ver |
|----|-------------|-----|
| R6.1 | MUST on period miss: skip Period bonus only — never wipe best streak, titles, or completed Steps | v0.2 |
| R6.2 | MUST provide fixed N-of-M daily and weekly Period bonuses; weekly worth more than daily | v0.2 |
| R6.3 | MUST treat extra completions beyond N as optional glory, not required for a “good” period | v0.2 |
| R6.4 | SHOULD weight weekly motivation higher than daily (daily stays a light CTA) | v0.2 |

## R7 — Anti-burnout & overhead

| ID | Requirement | Ver |
|----|-------------|-----|
| R7.1 | MUST keep gamification from outranking Due now / high-priority needed work on Today | all |
| R7.2 | SHOULD minimize setup/admin overhead vs doing the work | all |
| R7.3 | UI/docs MUST read as a personal productivity tool, not a game | v0.2 |

## R8 — AI-assisted planning

| ID | Requirement | Ver |
|----|-------------|-----|
| R8.1 | MUST define a stable ingest schema + LLM instruction doc for Epic→Phase→Step plans | v0.3 (stub MAY land earlier) |
| R8.2 | MUST support import modes **New** and **Update** | v0.3 |
| R8.3 | Update MUST NOT silently delete or reset completed Steps / Phase progress | v0.3 |
| R8.4 | Destructive Update MUST require explicit confirmation | v0.3 |

## R9 — Documentation process

| ID | Requirement | Ver |
|----|-------------|-----|
| R9.1 | MUST keep core requirements in `docs/` in this repository | all |
| R9.2 | MUST record material product changes in DECISIONS.md | all |
| R9.3 | Developer and Tester MUST treat merged docs as source of truth over chat | all |
