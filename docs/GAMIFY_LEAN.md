# v1.2 Gamify-lean architecture

**Status:** PO-locked direction (2026-09-10) — normative for `feat/v1.2-gamify-lean`  
**Tone:** GW2-style cosmetics / titles. Points buy *how the app looks*, not IRL breaks. UX extremely lean.

## Goals

1. Replace IRL break/snack/meal shop with a **fixed cosmetic + title unlock catalog**.
2. **Lean create path:** new user → starter template **or** paste LLM plan → land on Today. Advanced Epic fields stay behind “Advanced.”
3. Completing Steps feels like ticking achievement bits (celebration toast / title unlock moment), not filling tickets.
4. No DIY rewards, no IRL “Done in real life,” no new form sprawl.

## Non-goals (Tester: push back if these appear)

- IRL redeem items / `fulfilled_irl` / break vouchers  
- User-defined shop prices or catalog  
- Extra Settings pages for cosmetics (equip from `/shop` or a one-click “Wear”)  
- Dual Active Epic, heat-maps, cloud, multi-user  
- Cartoon RPG chrome on Due now / Active Epic (R7.1 still holds)

---

## A. Cosmetic catalog (fixed SKUs)

Code constant in `app/shop.py` (same pattern as today). **No DB catalog table.**

### SKU shape

```text
ShopItem {
  id: str              # stable catalog_id
  kind: "theme" | "title" | "badge_frame" | "today_flair"
  label: str           # display name
  cost: int            # points
  unlock_payload: str  # CSS class / title string / flair id
}
```

### Proposed v1 catalog (fixed — Designer/PO may rename labels, not structure)

| catalog_id | kind | Label | Cost | Effect |
|------------|------|-------|-----:|--------|
| `theme_aurora` | theme | Aurora theme | 80 | `data-theme` / CSS class on `<html>` |
| `theme_ember` | theme | Ember theme | 120 | same |
| `title_pathfinder` | title | Title: Pathfinder | 100 | string under username in topbar |
| `title_steady` | title | Title: Steady Hand | 150 | same |
| `title_finisher` | title | Title: Finisher | 250 | same |
| `frame_bronze` | badge_frame | Bronze badge frame | 60 | CSS on points pill |
| `frame_silver` | badge_frame | Silver badge frame | 140 | same |
| `flair_spark` | today_flair | Today spark flair | 90 | subtle CSS on Active Epic card |

Prices stay in the same ballpark as the old IRL catalog (40–500). Exact numbers adjustable before CLEAR; **IDs are frozen once shipped.**

### Ownership / equip

- **Unlock** = spend points once → row in `redemptions` (reuse table) with `catalog_id`.  
- **Equip** = which unlocked cosmetic is active:
  - Store on `users` as nullable columns (no new tables):  
    `equipped_theme`, `equipped_title`, `equipped_badge_frame`, `equipped_today_flair` (each holds a `catalog_id` or null).  
  - Equip is a **single POST button** on `/shop` (“Wear”) — not a form with many fields.
- One equipped item per kind. Unlocking does not auto-equip (player chooses) **except** first unlock of a kind may auto-equip to make the moment land.

### Kill IRL shop

- Remove catalog entries `break_15`, `snack`, `media_ep`, `hobby_hour`, `meal_out`, `half_day`.  
- Remove `fulfilled_irl` UI and route. Column may remain unused for export compatibility or be ignored in UI (prefer: stop writing it; export keeps field as always false).  
- Rewrite `docs/REWARD_SHOP.md` → cosmetics/titles.  
- Update PRODUCT core loop step 7 and R3.x wording: spend = cosmetics, not treats.

### Migration / existing redemptions

- Old IRL `catalog_id` rows: show under Shop history as “Legacy IRL reward (retired)” — no fulfill toggle. Points already spent stay spent.  
- No refunds automation.

---

## B. Title unlocks (feel)

- Equipped title renders under username:  
  `{{ user.username }}` + muted line `{{ equipped_title_label }}`.  
- On unlock (redeem of `kind=title`): flash toast on next Today load — short, one line (“Title unlocked: Pathfinder”).  
- Completing a Step / Phase / Epic: keep existing point grants; add a **small celebration toast** (CSS + auto-dismiss) when flash contains completion language — no modal.

---

## C. Lean create flow

### First-run / empty state

Priority order on Today / Epics empty:

1. **Pick a starter template** (existing three life-mode templates) — one click → creates Epic via existing ingest `mode:new` → Active → redirect `/today`.  
2. **Paste LLM plan** — single textarea + one Submit (existing `/import` path, simplified entry from empty CTA).  
3. Link: “Advanced create…” → current full Epic form (phases/steps) **collapsed behind Advanced**.

### Epic create form (when Advanced)

Visible by default if Advanced opened:

- Title (required)  
- Path: Full / Focused (segmented control, not a long explanation)  

Behind `<details>` Advanced:

- Life mode, preview, phase deliverables, parent epic, free-form phase/step builders  

Template + LLM paths never show Advanced.

### Out

- No new multi-page wizards.  
- No extra Settings for “create preferences.”

---

## D. Implementation slices (suggested PR order)

| Slice | Scope | Gate note |
|-------|--------|-----------|
| **G1** | Docs + catalog constant swap + shop UI copy; remove IRL fulfill UI; legacy history label | Tester: zero new form fields |
| **G2** | User equip columns + Wear buttons; apply theme/title/frame/flair in base/Today | Still one-click Wear |
| **G3** | Unlock / completion toasts | No dialogs |
| **G4** | Lean empty-state CTAs (template / paste / Advanced) | Count form fields — Advanced only |

Branch: `feat/v1.2-gamify-lean` → PRs into `dev` per slice (or one PR if tight).

---

## E. Acceptance sketch (v1.2 gamify)

1. `/shop` lists only cosmetic/title SKUs; no IRL items; no “Done in real life.”  
2. Redeem spends points; Wear equips without a multi-field form.  
3. Equipped title visible under username; theme/flair/frame visible without Settings.  
4. Empty path: template or LLM paste → Today; Advanced create is opt-in.  
5. R7.1: shop / cosmetics never reorder Due now / Active Epic.  
6. No DIY catalog; pytest covers catalog ids + redeem/equip + lean CTA presence.

---

## F. Explicit rejects

| Ask | Answer |
|-----|--------|
| Keep snack/break as optional SKUs | **No** — fantasy is cosmetics only |
| DIY “create my own title” | **No** |
| Theme toggle in Settings (BL-024) | **Superseded** — themes are shop unlocks |
| More settings pages | **No** |
