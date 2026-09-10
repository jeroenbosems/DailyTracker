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

## v0.4 (shipped)

- [x] Life modes + Today filter chips (section order fixed); starter templates; docs + NFRs

## v0.5 (shipped)

Must pass before merge:

1. **Fixed catalog** — code constant only (`break_15` 40, `snack` 80, `media_ep` 100, `hobby_hour` 150, `meal_out` 300, `half_day` 500); no UI DIY / user-defined prices
2. **Data** — `redemptions` with `user_id`, `catalog_id`, `points_spent`, `created_at`, `fulfilled_irl`
3. **Redeem** — if `total_points < cost` → HTTP 400 clear error; else subtract points + insert redemption
4. **UI** — `/shop` catalog + redeem + history with “Done in real life” toggle; nav link; Today pts link to shop only — **never** a shop section above Due now / Active Epic
5. **Docs** — ACCEPTANCE/PRODUCT + `docs/REWARD_SHOP.md` listing catalog; adult productivity copy
6. **R2.*** / **R1.*** / **R7.1** / **R3.4** — prior NFRs still hold

Out of scope for this gate: RNG, user-defined rewards/prices, follow-on Epic.


## v0.6 (shipped)

Must pass before promote `test` → `release`:

1. **Explicit CTA** — completed Epic detail + Today celebration show **Start follow-on**; no auto-start without confirm/submit
2. **New Epic** — creates via `follows_epic_id` pointing at the completed Epic; completed Epic fields unchanged (no wipe/mutate)
3. **Prefill** — title `Follow-on: {title}`, identity/capability from parent with refine/maintain tone, same life modes, path default **Focused**, editable Stabilize / Improve starter Phases+Steps
4. **Links** — new Epic shows “Follows: …”; completed Epic shows “Follow-ons” links
5. **Today / Active** — behavior unchanged aside from the celebration CTA
6. **Docs** — ACCEPTANCE/PRODUCT/DECISIONS (+ optional FOLLOW_ON.md)
7. **Prior NFRs** — R2.* / R1.* / R7.1 still hold

Out of scope: auto-starting follow-ons; DIY reward changes.


## v0.7 (shipped)

Must pass before promote `test` → `release`:

1. **Export** — authenticated GET from Settings downloads JSON with `schema_version`, `exported_at`, tasks, routines, epics(+phases+steps), reward_logs, redemptions; **no** password hashes / session secrets
2. **Restore merge** — create missing by `external_id`; never overwrite completed Steps
3. **Restore replace** — wipe user product data then import; requires typed `REPLACE` + checkbox
4. **Schema** — reject unknown `schema_version`
5. **UI** — Settings page only; no export/restore clutter on Today
6. **Docs** — ACCEPTANCE/PRODUCT/DECISIONS (+ EXPORT_BACKUP.md)
7. **Out** — cloud sync; auto-backup outside the Docker volume


## v0.8 (shipped)

Must pass before promote `test` → `release`:

1. **Watch pins** — `watch_items` in export/restore (kind + ref_external_id); pins round-trip; replace wipe still clears then restores from payload
2. **Empty states** — Today / Epics / Shop each show one clear productivity CTA when empty
3. **Docs** — PRODUCT roadmap marks shipped slices through v0.7+; ACCEPTANCE current gate = v0.8
4. **Out** — no new game systems


## v0.9 (shipped)

Must pass before promote `test` → `release`:

1. **`/review`** — read-only weekly snapshot: completed Tasks/Routines/Steps this ISO week; Active Epic % + next Step; points earned; daily/weekly Period bonus status
2. **Entry** — nav link + Today footer link only (no Today board clutter)
3. **CTA** — one primary “Back to Today”
4. **Out** — email/push notifications; editing from review


## v1.1 (shipped — core BL-020/021/031)

Core slices shipped to main.

1. **BL-020 Search** — `/search` title substring across Tasks/Routines/Epics/Steps; results link out; **does not** reorder Today (R7.1)
2. **BL-021 Soft archive** — hide/restore Epics; never wipe progress (later PR)
3. **BL-031 Routine skip** — soft skip with reason; no streak wipe (later PR)

Out: dual Active, heat-map, DIY/cloud/multi-user.

## v1.2 (in progress)

Must pass before promote `test` → `release`:

1. **BL-023 Keyboard shortcuts (Today)** — `c` completes next Step; `r` opens `/review`; ignored while typing; legend in Today footer
2. Further planned backlog items as locked by PO

## v1.2 G1 (cosmetic shop catalog)

1. `/shop` lists only cosmetic/title SKUs; no IRL items; no “Done in real life”
2. Unlock spends points; unknown/DIY ids rejected
3. Legacy IRL redemptions (if present) labeled retired in history
4. R7.1: no shop card above Due now / Active Epic

## v1.2 G2 (Wear equip)

1. One-click POST `/shop/wear` with `catalog_id` only
2. Equipped theme/title/frame/flair apply without Settings
3. No multi-field equip form; no Settings cosmetics chrome

## How to report

Pass / fail per ID. Separate **product gaps** (PO) from **defects** (Developer).

## BL-023 Keyboard shortcuts (Today)

- On `/today`, `c` completes the Active Epic next Step (same as Complete Step); `r` navigates to `/review`.
- Shortcuts do not fire while focus is in an input, textarea, select, or contenteditable.
- Legend is visible in the Today page footer (optional, discoverable).
