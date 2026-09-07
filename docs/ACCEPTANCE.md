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

## v0.3 (shipped)

- [x] R5.12 — Explicit Park clears Active; Parked never wipes progress; Today calm “Parked · N”
- [x] R8.1–R8.4 — LLM ingest New/Update; destructive confirm; `/import`
- [x] Docs + prior NFRs

## v0.3.1 (shipped)

- [x] Reward history `/rewards`; Watch / Nearly done max 6; docs + NFRs

## v0.3.2 (shipped)

Must pass before merge:

1. **Epic.path** — `full` | `focused` (default full) on create form + LLM ingest
2. **Phase.parked** — Full→Focused prefers parking non-focused Phases (keep first 2); `confirm_destructive` only to remove **incomplete** extras; never silent wipe of completed work
3. **Focused→Full** — unpark all; add missing Phases/Steps toward fuller structure without wiping progress
4. **Today / next Step / Nearly done** — ignore parked Phases
5. **UI** — Full/Focused badge; explicit switch control + clear flash messages; no silent loss
6. **Docs** — this gate; brief PRODUCT/DECISIONS note
7. **R2.*** / **R1.*** / **R7.1** — prior NFRs still hold

Out of scope for this gate: life-mode filters, reward shop, follow-on Epic.

## v0.4 (current gate)

Must pass before merge:

1. **Life modes** — enum `work|health|home|learning`; optional single `life_mode` on Task/Routine/Step; Epic multi-select as JSON text `life_modes` default `[]`
2. **Today filter chips** — All + each mode; **never reorder** sections (Due now → Active Epic → Watch/Nearly done → Period bonuses); filter only hides/shows within lists
3. **Filter rule** — under a mode: show tagged that mode **OR untagged**; All shows everything
4. **Forms** — mode select on create task/routine/step/epic; epic multi checkbox
5. **Starter templates** — `docs/templates/{side-it-project,move-house,apartment-redo}.json` valid `mode:new` payloads; “Start from template” on `/epics` and `/import` creates new only (never mutates existing)
6. **Docs** — LLM_INGEST examples/links; PRODUCT + this gate bumped for v0.4
7. **R2.*** / **R1.*** / **R7.1** — prior NFRs still hold

Out of scope for this gate: reward shop, follow-on Epic.

## How to report

Pass / fail per ID. Separate **product gaps** (PO) from **defects** (Developer).
