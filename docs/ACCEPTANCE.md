# Daily Tracker — Acceptance gates

Tester owns execution. PO owns the bar. Map fails to REQUIREMENTS.md IDs.

## v0.1 (shipped)

- [x] R1.* Docker Compose + volume + local-only
- [x] R2.* Auth argon2/bcrypt, cookie flags, graceful errors
- [x] R3.* Tasks, Routines, fixed Priority rewards
- [x] R4.1–R4.3 Due now rules (no undated in Due now)

## v0.2 (shipped)

- [x] R5.1–R5.3, R5.10–R5.11 — Epic → Phase → Step; next Step + % Phase + % Epic; Active Epic Step on Today; celebration scale
- [x] R5.4–R5.6 — optional parent Epic; Step↔Task/Routine links when present; parallel Steps
- [x] R5.7–R5.9 — identity/capability fields; Phase deliverable + Epic preview
- [x] R6.* — soft miss never wipes progress; N-of-M daily + weekly Period bonuses (weekly > daily); extras optional
- [x] R7.1, R7.3 — needed work not outranked by vanity; productivity tone in UI + PRODUCT.md
- [x] R2.* / R1.* — prior NFRs still hold
- [x] Docs: REQUIREMENTS.md + PRODUCT.md + this file reflect v0.2 (MOTIVATION.md non-normative)

## v0.3 (current gate)

Must pass before merge:

1. **R5.12** — Explicit Park action clears Active when that Epic was Active; Parked never wipes progress/titles/completions; Today surfaces only Active Epic + calm “Parked · N” link to `/epics` (no guilt copy); Park button on list + detail when Active; Parked badge already on list/detail
2. **R8.1–R8.4** — Stable `external_id` on Epic/Phase/Step; `app/ingest.py` validates against `docs/LLM_INGEST.md`; modes `new` | `update`; update refuses silent delete of completed Steps / progress reset; destructive removals need JSON `confirm_destructive: true` **and** UI checkbox; `/import` page with flash/errors (no raw stacks); Import in nav (Today/Epics); successful new with `status: active` (or first Epic) activates without punishing other Parked Epics
3. **Docs** — this gate checklist; LLM_INGEST status implemented; REQUIREMENTS version tags (v0.2 shipped, v0.3 in progress); DECISIONS note if useful
4. **R2.*** / **R1.*** — prior NFRs still hold (argon2/cookies unchanged)

Out of scope for this gate: Full vs Focused paths, reward history page, watch list.

## How to report

Pass / fail per ID. Separate **product gaps** (PO) from **defects** (Developer).
