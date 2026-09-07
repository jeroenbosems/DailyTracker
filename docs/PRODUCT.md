# Daily Tracker — Product pack (through v1.6)

Source of truth for product decisions. Implementation lives in this repo and ships via Docker Compose.

**Status:** packs v1 → v1.6 folded in  
**Product:** personal productivity tool for ambitious solo work  
**Inspiration:** Guild Wars 2 achievement *design lessons* only — this is **not** a game tracker (see [MOTIVATION.md](./MOTIVATION.md)).

## Positioning

> The Guild Wars 2 achievement panel for your real life — progress, next step, and fair rewards, without Jira ceremony or Habitica homework.

We are **not** building a GW2 tracker. Vault / Griffon / Skyscale / legendaries are research inspiration only. Success = tangible progress on high-value items toward an ambitious target over days/weeks/months — not “earned gold in an app.”

## Problem

1. Ambitious personal targets die mid-way (moving house, apartment redo, side IT projects, fitness, learning).
2. Tools create overhead / board theater — rearranging work instead of doing high-value work.
3. Team tools (Jira / Trello / Azure DevOps) punish solo users with coordination primitives and no motivation design.
4. DIY reward systems drift; brittle streaks and punishment cause burnout.

## Outcome

Users fill days with **useful** work, feel **progress** and fair **reward**, and keep a foot in the door on non-standard projects — without burnout or admin becoming the job.

## Anti-patterns (explicit)

| Avoid | Why |
|-------|-----|
| Quantity-Karma farming | Priority / impact tiers beat checkmark count |
| DIY point / shop economies | Drift, inflation, collapse of meaning |
| Habitica-style HP / guilt spirals | Miss slows; never wipe best streak, titles, or completed Stories |
| Cartoon RPG / MMO chrome in UI | Adult productivity tool — no pets, loot, HP |
| Status theater / field tax | Capture cheaper than thought |
| Extrinsic rewards on already-fun work | Prioritize needed / formation work + milestones |
| 100%-or-fail dailies | N-of-M “enough is enough”; extras = optional glory |
| Gamification outranking Due now | Needed work always sorts above vanity |

## Naming (locked)

| Term | Meaning | Typical scale |
|------|---------|----------------|
| **Epic** | Ambitious outcome the user cares about (Legendary when flagged) | Months |
| **Act** | Chapter / Feature toward an Epic with its own finish line | Weeks |
| **Story** (Bit in code) | Concrete next action toward an Act | Days |
| **Task** | One-off work item (may link to a Story) | Days |
| **Routine** | Recurring work (daily / weekly / monthly / yearly) | Recurring |
| **Active Epic** | The Epic Today prioritizes | — |
| **Parked Epic** | Epic kept without Today pressure; parking is not failure | — |
| **Today** | Daily board | Day |
| **Due now** | Overdue + due today (+ routines due) | Day |
| **Priority reward** | Fixed Gold / Silver / Bronze by priority 1 / 2 / 3 | On completion |
| **Period bonus** | N-of-M daily or weekly completion bonus (fixed; weekly > daily) | Day / week |

UI + docs use **Epic / Act / Story**. Game metaphors stay in MOTIVATION.md as design rationale only.

## Ontology — Epic → Act → Bit

Scale model (pack v1.4):

| Scale | Delivery language | Entity |
|-------|-------------------|--------|
| Months | Epic | **Epic** (Legendary) — chaptered Acts, identity + capability end state |
| Weeks | Feature | **Act** — mid finish line inside an Epic |
| Days | User story | **Story / Bit** — today’s concrete next step |

Rules:

1. Every Epic decomposes into ≥2 Acts; every Act into day-scale Stories.
2. Today surfaces the **next incomplete Story** of the Active Epic (needed work), not random busywork.
3. Celebrations scale: Story < Act < Epic.
4. If it fits in a day → Story; needs a week of sessions → Act; needs many Acts → Epic.
5. Period bonuses support the daily CTA; they must never be the only motivation system.

## Legendary rules (pack v1.3)

A Goal may be marked **Legendary** (high ambition):

- Ordered **Acts**, each with its own Stories + Act-complete celebration.
- Always show: next Story, % in current Act, % overall.
- Prefer **parallel Stories** inside an Act (any order) so a session never stalls; Acts may be sequenced.
- **Preview** of the end state (user-defined taste) unlockable mid-journey (~25% overall).
- **Intermediate deliverables** per Act (real usable outcomes), not only a progress %.
- End state = **identity + capability** fields (what unlocks in real life), not points alone.
- Soft miss: period miss skips Period bonus only — never wipe best streak, titles, or completed Stories.
- Post-complete Follow-on / Mastery Epic and Full vs Focused paths → **v0.3**.

## Soft streak & Period bonuses (N-of-M)

- **Soft streak (routines):** a miss resets **current** streak only; **never** wipe `best_streak`.
- **Period bonuses:** fixed N-of-M daily and weekly defs (weekly worth more than daily). Hitting N opens the bonus; hitting M grants optional glory. Extra completions beyond N are optional, not required for a “good” period.
- Missing a period = no grant that period — progress rows are per-period keys, never wiped historically.
- Daily stays a light CTA; weekly carries more motivational weight.

## Preview & intermediate deliverables (pack v1.6)

1. **Preview early** — taste the end state mid-journey.
2. **Intermediate real deliverables** — each Act ships something usable in life.
3. Celebrate 1st Story, midpoint, Act done, Epic done — not only 100%.
4. Soft parallel Stories + serial Acts when order matters.
5. Always one doable Story today toward the Active Epic.

## Core objects

### Task (v0.1)

One-off work item: title, optional notes, priority 1–3 (1 = needed), optional due date, completed flag + timestamp.

### Routine (v0.1)

Cadence `daily` \| `weekly` \| `monthly` \| `yearly`; same priority model; streak, best streak, completion count, last completed, next due.

### Reward (v0.1)

Fixed tiers only (never user-defined points):

| Tier | Priority | Points |
|------|----------|--------|
| Gold | 1 | 50 |
| Silver | 2 | 25 |
| Bronze | 3 | 10 |

Plus fixed Act / Epic / Period-bonus grants. Every grant is logged; UI shows total points.

### Epic / Act / Story (v0.2)

See ontology + Legendary rules above. Stories may optionally link to a Task and/or Routine.

## Today / Due-now (product rules)

- **Surface:** overdue items, due today, and routines whose `next_due ≤ today`.
- **Do not** put undated open tasks in Due-now (they stay under Open tasks).
- **Sort:** priority ascending (1 first), then due date ascending, then created.
- Needed work beats fun busywork: priority 1 always above 2/3.
- Gamification (Epic panel, period bonuses) **never outranks** Due-now sorting.
- Completing a routine advances `next_due` by cadence; soft streak on miss.

## UX flows

**v0.1:** Setup → Login → Today → Create task/routine → Complete → Reward feedback + streak/points → Logout.

**v0.2 adds:** Create Epic (≥2 Acts, Stories newline-separated) → Activate → Today shows next Story + Act% + overall% + period bonuses → Complete Story (and/or linked task/routine) → Act/Epic celebrations + soft period bonuses.

Graceful error pages (no raw stacks). Data persists in a named Docker volume.

## Explicit non-goals

Multi-user, cloud sync, mobile apps, OAuth/IdP, custom reward economies, integrations (Jira/Trello/etc.), telemetry, mandatory social features, game-first UI.

## NFR bar

- Local auth (argon2 preferred / bcrypt acceptable)
- Session cookies: HttpOnly + SameSite=Lax (+ Secure if TLS)
- All data in the container volume
- No secrets in repo
- No outbound telemetry/PII by default
- Graceful errors; fine for single-user solo use

## Sequence

| Version | Scope |
|---------|--------|
| **v0.1** (done) | Auth + tasks + routines + today/due-now + fixed rewards/streaks + Docker |
| **v0.2** (this) | Epic → Act → Story, Active Epic on Today, N-of-M period bonuses, soft miss, preview + Act deliverables, docs through pack v1.6 + MOTIVATION.md |
| **v0.3** (later) | Parked Epics polish, LLM ingest New/Update, Full vs Focused paths, reward history, watch list / nearly-done, life-mode filters, follow-on / Mastery Epic, optional fixed reward shop |

Product decisions land with the Product Owner. Chat is not requirements — this file wins once merged.
