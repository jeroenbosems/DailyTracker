# Decision log

Append-only. Newest first. Chat opinions do not count until recorded here and reflected in REQUIREMENTS.md / PRODUCT.md.

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
