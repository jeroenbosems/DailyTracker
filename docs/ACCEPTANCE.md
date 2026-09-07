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

## v0.3.1 (current gate)

Must pass before merge:

1. **Reward history** — `/rewards` lists `RewardLog` newest first (tier badge, points, reason, timestamp); read-only; nav link + link from Today “Recent rewards”; still no DIY economy (R3.4)
2. **Watch / Nearly done (max 6)** — Today card **below** Due now + Active Epic, **above** Period bonuses (R7.1)
   - Pinned Steps and open Tasks in `watch_items` (user_id, kind step|task, ref_id, created_at); unique (user, kind, ref); hard cap **6** with clear error when full
   - Auto Nearly done fills remaining slots: incomplete Steps that are (a) last incomplete in Phase, or (b) Phase progress ≥ 80%; Active Epic first; dedupe vs pins; drop completed refs from display (clean pins on complete when easy)
   - UI: pinned vs auto badge; unpin/pin on Epic detail Steps and Open tasks where cheap
3. **Docs** — this gate checklist; brief PRODUCT/DECISIONS note
4. **R2.*** / **R1.*** / **R7.1** — prior NFRs still hold

Out of scope for this gate: Full vs Focused Epic paths, life-mode filters, follow-on Epic.

## How to report

Pass / fail per ID. Separate **product gaps** (PO) from **defects** (Developer).
