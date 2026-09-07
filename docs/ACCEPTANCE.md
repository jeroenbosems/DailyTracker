# Daily Tracker — Acceptance gates

Tester owns execution. PO owns the bar. Map fails to REQUIREMENTS.md IDs.

## v0.1 (shipped)

- [x] R1.* Docker Compose + volume + local-only
- [x] R2.* Auth argon2/bcrypt, cookie flags, graceful errors
- [x] R3.* Tasks, Routines, fixed Priority rewards
- [x] R4.1–R4.3 Due now rules (no undated in Due now)

## v0.2 (current gate)

Must pass before merge:

1. **R5.1–R5.3, R5.10–R5.11** — Epic → Phase → Step; next Step + % Phase + % Epic; Active Epic Step on Today; celebration scale
2. **R5.4–R5.6** — optional parent Epic; Step↔Task/Routine links when present; parallel Steps
3. **R5.7–R5.9** — identity/capability fields; Phase deliverable + Epic preview when in PR
4. **R6.*** — soft miss never wipes progress; N-of-M daily + weekly Period bonuses (weekly > daily); extras optional
5. **R7.1, R7.3** — needed work not outranked by vanity; productivity tone in UI + PRODUCT.md
6. **R2.*** / **R1.*** — prior NFRs still hold
7. Docs: REQUIREMENTS.md + PRODUCT.md + this file reflect v0.2 (MOTIVATION.md non-normative)

## v0.3 (planned gate)

- Parked Epic UX (R5.12)
- LLM ingest New vs Update (R8.*) with no silent progress wipe
- Optional Full vs Focused Epic paths; reward history; nearly-done / watch list as scoped

## How to report

Pass / fail per ID. Separate **product gaps** (PO) from **defects** (Developer).
