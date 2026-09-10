## 2026-09-10 — G2 Wear equip columns

**Decision:** `users.equipped_*` columns; one-click `/shop/wear`; first unlock of a kind auto-equips; apply via Jinja globals + `data-theme` / CSS classes. No Settings theme UI.
**Why:** GAMIFY_LEAN G2 under Tester hard constraints.
**Affects:** models; database migrate; shop; base/today templates; style.css

## 2026-09-10 — Pivot: GW2-style cosmetics + lean UX (v1.2)

**Decision:** Kill IRL break/snack shop fantasy. Points buy **fixed cosmetic / title / badge-frame / Today-flair SKUs**. Equip via one-click Wear (columns on `users`). Lean create: template or LLM paste → Today; full Epic form behind Advanced. Stop backlog polish (BL-024 closed). Architecture: `docs/GAMIFY_LEAN.md`. Branch `feat/v1.2-gamify-lean`.
**Why:** Client/PO: fun gamification + extremely lean UX; IRL vouchers felt like admin software.
**Affects:** shop.py; REWARD_SHOP; PRODUCT; Today/Epics empty CTAs; users equip columns; supersedes BL-024 Settings theme PR

# Decision log

Append-only. Newest first. Chat opinions do not count until recorded here and reflected in REQUIREMENTS.md / PRODUCT.md.

## 2026-09-10 — BL-023 Today keyboard shortcuts

**Decision:** On Today only: `c` submits the next-Step complete form; `r` goes to `/review`. Legend in Today footer; ignore when focus is in form fields. No chords — keep optional and conflict-free with typing.
**Why:** 1.2 first backlog item (was stretch); PO ordered start after Mac Start here.
**Affects:** today.html; static/today-shortcuts.js; ACCEPTANCE/PRODUCT

## 2026-09-10 — Mac-clear Start here

**Decision:** README Start here calls out **Mac / Linux** vs **Windows** explicitly; Mac tip points at Docker Desktop for Mac + whale-idle before `./start.sh`.
**Why:** Client on Mac asked for clear Mac instructions (same command as Linux).
**Affects:** README; scripts/start.sh error hints

## 2026-09-10 — One-action Docker start at repo root

**Decision:** Add root `./start.sh` / `./start.ps1` wrappers, wait-for-ready messaging, `scripts/stop.sh`, compose healthcheck, and VS Code build task. README leads with **Start here**.
**Why:** Client could not see a single obvious action to spin up Docker.
**Affects:** README; start scripts; docker-compose healthcheck

## 2026-09-09 — v1.1 reopen (Search → soft archive → routine skip)

**Decision:** Client reopened after v1.0-rc freeze for 1.1: BL-020 Search, BL-021 Soft archive, BL-031 Routine skip (stretch BL-023). Out: dual Active, heat-map, DIY/cloud/multi-user.
**Why:** Keep shipping value while Docker smoke waits on client.
**Affects:** backlog; ACCEPTANCE v1.1; feat/v1.1-search

## 2026-09-08 — v1.0-rc shippable cut

**Decision:** After v0.9 on main, tag `v1.0-rc` once Tester smoke passes (fresh clone → start script → setup → template Epic → Step → redeem/export). README gets a Shippable RC section. Feature freeze to bugfixes only until v1.0 or reopen.
**Why:** Client asked for a stable, workable, easily runnable release.
**Affects:** README; release tagging; GitFlow freeze policy

## 2026-09-08 — v0.9 Weekly review

**Decision:** Add read-only `/review` for the current ISO week (completions, Active Epic %, points, Period bonus status). Entry via nav + Today footer only; single CTA Back to Today. No email/push.
**Why:** Light shippable stability slice toward a workable release.
**Affects:** ACCEPTANCE v0.9; PRODUCT roadmap; `app/review.py`

## 2026-09-08 — v0.8 Polish (Watch export + empty CTAs)

**Decision:** Include WatchItem pins in JSON export/restore; add one clear empty-state CTA on Today, Epics, and Shop; mark shipped roadmap slices in PRODUCT/ACCEPTANCE. No new game systems.
**Why:** Tester note on v0.7 + light polish before next feature slice.
**Affects:** backup.py; Today/Epics/Shop templates; PRODUCT roadmap; ACCEPTANCE v0.8

## 2026-09-08 — v0.7 Export & backup

**Decision:** Settings-only JSON export/restore. Export strips secrets. Restore modes: merge (create-missing by external_id; never overwrite completed Steps) and replace (wipe then import) with typed REPLACE + checkbox. Reject unknown schema_version. No cloud sync.
**Why:** Locked v0.7; portable backup without silent wipe risk.
**Affects:** ACCEPTANCE v0.7; PRODUCT; docs/EXPORT_BACKUP.md; GitFlow `feat/v0.7-export-backup` → dev

## 2026-09-08 — v0.6 Follow-on Epic

**Decision:** When an Epic completes, offer explicit **Start follow-on** (detail + Today). Creates a **new** Epic with `follows_epic_id` → completed one; never mutates/wipes the completed Epic. Prefill title/identity/capability/life modes; default Focused with editable Stabilize/Improve starters. Bidirectional Follows / Follow-ons links.
**Why:** Locked v0.6 scope; refine/maintain without destroying history.
**Affects:** ACCEPTANCE v0.6; PRODUCT roadmap; GitFlow into `feat/v0.6-follow-on` → `dev`

## 2026-09-08 — Long-lived GitFlow branches

**Decision:** Use four long-lived branches — `main`, `release`, `test`, `dev` — plus short-lived `feat/*` / `fix/*` / `hotfix/*`.

**Flow:**
1. Developer cuts `feat/*` (or `fix/*`) from `dev` → PR into `dev`.
2. When a slice is ready for acceptance, promote `dev` → `test` (PR). Tester gates against ACCEPTANCE on that PR / `test` tip.
3. On **CLEAR**, promote `test` → `release` (PR). Stabilize only; no new scope.
4. Ship: promote `release` → `main` (PR). `main` is what runs in production / real use.
5. Hotfixes: `hotfix/*` from `main` → PR into `main`, then back-merge into `release` and `dev`.

**Why:** Client asked for proper GitFlow visibility (`dev` / `test` / `release` / `main`); separates integration, acceptance, release candidate, and prod.
**Affects:** Team process; replaces “feature PR merges straight to main” for product code.

## 2026-09-08 — v0.5 Fixed reward shop

**Decision:** Ship a fixed reward catalog (code constant) and `/shop` redeem + history with `fulfilled_irl`. Underfunded redeem returns HTTP 400. Today only links pts to the shop — no shop section above Due now / Active Epic. No RNG or user-defined rewards/prices.
**Why:** Cleared v0.5 scope; spend earned points on real breaks without DIY inflation (R3.4, R7.1).
**Affects:** ACCEPTANCE v0.5; PRODUCT roadmap; docs/REWARD_SHOP.md

## 2026-09-07 — v0.4 Life modes + starter templates

**Decision:** Optional life-mode tags (`work|health|home|learning`): single nullable on Task/Routine/Step; Epic multi as JSON `life_modes` default `[]`. Today filter chips (All + modes) hide/show within fixed section order; under a mode show tagged OR untagged. Starter templates under `docs/templates/` are `mode:new` ingest only — Start from template never mutates existing Epics. Reward shop stays out.
**Why:** Cleared v0.4 scope; filter without board theater; capture cheaper via templates.
**Affects:** R4.7, R5.14, R8.5; ACCEPTANCE v0.4; PRODUCT roadmap

## 2026-09-07 — v0.3.2 Full vs Focused Epics

**Decision:** Epics have path full|focused. Focused parks extra Phases by default; explicit confirm only removes incomplete extras. Full unparks and may add Phases/Steps without wiping completed work. Today/next Step/Nearly done skip parked Phases.
**Why:** Cleared v0.3.2 scope.
**Affects:** ACCEPTANCE v0.3.2; PRODUCT roadmap

## 2026-09-07 — v0.3.1 Watch + reward history

**Decision:** Ship read-only `/rewards` history and Today **Watch / Nearly done** (max 6: user pins + auto nearly-done Steps). Card stays below Due now / Active Epic. Full vs Focused paths remain out.  
**Why:** Cleared v0.3.1 scope; surface progress without DIY economy or vanity outranking needed work (R7.1).  
**Affects:** ACCEPTANCE v0.3.1; PRODUCT roadmap

## 2026-09-07 — v0.3 Park + LLM ingest gate

**Decision:** Ship explicit Park (clears Active only; progress stays) and LLM JSON ingest New/Update with `external_id` matching; destructive removals need JSON + UI confirm. Full/Focused paths, reward history, and watch list stay out of this gate.  
**Why:** Tester-cleared v0.3 scope; R5.12 polish + R8.* without silent progress wipe.  
**Affects:** R5.12, R8.*, ACCEPTANCE v0.3

## 2026-09-07 — Docs are the contract

**Decision:** Core requirements live in `docs/` (REQUIREMENTS, PRODUCT, ACCEPTANCE, DECISIONS). Chat is input only.  
**Why:** Requirements change; chat history is a poor tracker for Developer/Tester.  
**Affects:** R9.*

## 2026-09-07 — Naming: Epic / Phase / Step

**Decision:** Use Epic → Phase → Step (not Act/Bit/Story/Chest in product UI). Period bonus replaces “chest.” Priority rewards keep Gold/Silver/Bronze as fixed tier labels.  
**Why:** PO owns naming; productivity language first; client gives vision only.  
**Affects:** PRODUCT.md naming; v0.2 model

## 2026-09-07 — Personal productivity, not a GW2 app

**Decision:** Product is a solo personal productivity framework for ambitious real-life targets. GW2 is design research only (MOTIVATION.md).  
**Why:** Client vision — foot in the door, high-value progress, anti-busywork, anti-burnout.  
**Affects:** R7.3, MOTIVATION.md

## 2026-09-07 — Active vs Parked Epics

**Decision:** One Active Epic on Today; other Epics may be Parked without punishment. Switching allowed when life requires; mono-grind is not the goal.  
**Why:** Prevent burnout; still fill days with useful work and felt progress.  
**Affects:** R5.11–R5.12, R7.*

## 2026-09-07 — Soft miss + Period bonuses

**Decision:** Miss skips Period bonus only; never wipe completed Steps / best / titles. N-of-M daily & weekly; weekly worth more; extras optional.  
**Why:** “Enough” beats all-or-nothing; mirrors proven soft cadence without Habitica punishment.  
**Affects:** R6.*

## 2026-09-07 — AI ingest New vs Update

**Decision:** LLM can author Epic plans via schema + prompt; New creates; Update patches by ID and must not silently destroy progress.  
**Why:** Everyone has AI; manual breakdown is overhead; bad AI Steps must be revisable.  
**Affects:** R8.* (v0.3)

## 2026-09-07 — Client engagement model

**Decision:** Client backs off; PO takes the wheel; return to client mainly to test ideas or for true blockers.  
**Why:** Explicit client preference.
