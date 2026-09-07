# Daily Tracker — Product

**Status:** authoritative with REQUIREMENTS.md  
**Product:** personal productivity tool for ambitious solo work  
**Inspiration:** Guild Wars 2 achievement *design lessons* only — this is not a game tracker (see MOTIVATION.md).

## Problem

1. Ambitious personal targets die mid-way (moving house, apartment redo, side IT projects, fitness, learning).
2. Tools create overhead / board theater — rearranging work instead of doing high-value work.
3. Team tools (Jira / Trello / Azure DevOps) punish solo users with coordination primitives and no motivation design.
4. DIY reward systems drift; brittle streaks and punishment cause burnout.

## Outcome

Users fill days with **useful** work, feel **progress** and fair **reward**, and keep a foot in the door on non-standard projects — without burnout or admin becoming the job.

## Naming (locked)

| Term | Meaning | Typical scale |
|------|---------|----------------|
| **Epic** | Ambitious outcome the user cares about | Months |
| **Phase** | Chapter toward an Epic with its own finish line | Weeks |
| **Step** | Concrete next action toward a Phase | Days |
| **Task** | One-off work item (may link to a Step) | Days |
| **Routine** | Recurring work (daily / weekly / monthly / yearly) | Recurring |
| **Active Epic** | The Epic Today prioritizes | — |
| **Parked Epic** | Epic kept without Today pressure; parking is not failure | — |
| **Today** | Daily board | Day |
| **Due now** | Overdue + due today (+ routines due) | Day |
| **Priority reward** | Fixed Gold / Silver / Bronze by priority 1 / 2 / 3 | On completion |
| **Period bonus** | N-of-M daily or weekly completion bonus (fixed; weekly > daily) | Day / week |

Do **not** use game-first UI copy (loot, chests, pets, HP). Game vocabulary may appear only in MOTIVATION.md as rationale.

## Core loop

1. Pick or resume an **Active Epic** (or work Due now / Routines).
2. Do the **next Step** (and other high-priority Due now items).
3. Complete → Priority reward + progress on Phase / Epic.
4. Hit N-of-M → **Period bonus** (enough is enough; extras optional).
5. Finish Phase → intermediate real deliverable + celebration.
6. Finish Epic → identity / capability outcome + optional follow-on Epic.

## Principles

1. **High-value over busywork** — Priority 1 and Active-Epic Steps outrank vanity.
2. **Always a next Step** — never a blank “what now?”
3. **Foot in the door** — Phases and intermediate deliverables; miss slows, never wipes.
4. **Anti-burnout** — light daily CTA; weekly carries more weight; Parked Epics allowed; overhead stays low.
5. **Fixed rewards** — no DIY point economies.
6. **Adult productivity UI** — clear progress, not cartoon RPG.
7. **Capture cheaper than thought** — especially via LLM ingest later.
8. **Docs over chat** — this folder is the contract.

## Non-goals

Multi-user, cloud sync, mobile apps, OAuth / IdP, custom reward economies, Jira/Trello integrations, telemetry, mandatory social features.

## Roadmap

| Version | Scope |
|---------|--------|
| **v0.1** | Auth, Tasks, Routines, Today / Due now, Priority rewards, Docker |
| **v0.2** | Epic → Phase → Step, Active Epic on Today, Period bonuses, soft miss, preview + Phase deliverable fields, docs refresh |
| **v0.3** | Parked Epics UX polish, LLM ingest New/Update, Full vs Focused Epic paths, reward history, watch list / nearly-done, life-mode filters, follow-on Epic |

PO owns product decisions and naming. Client provides vision only.
