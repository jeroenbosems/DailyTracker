# Decision log

Append-only. Newest first. Chat opinions do not count until recorded here and reflected in REQUIREMENTS.md / PRODUCT.md.

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
