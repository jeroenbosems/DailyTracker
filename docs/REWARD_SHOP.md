# Cosmetic shop — fixed catalog

**Status:** normative for v1.2 gamify-lean (G1+)  
**Tone:** GW2-style titles / themes / frames / flair. Points buy how the app looks — not IRL breaks.

See also: `docs/GAMIFY_LEAN.md`.

## Principles

1. **Fixed catalog only** — prices and items are a code constant. No user-defined rewards or prices.
2. **Earn then spend** — points come from Priority rewards and Period bonuses; the shop only spends.
3. **Today stays focused** — Shop lives on `/shop`. No shop section above Due now / Active Epic (R7.1).
4. **No IRL fulfill** — unlocks are cosmetics/titles. `fulfilled_irl` is unused in UI (schema kept for export compat).
5. **Wear (G2)** — equip is a one-click button, not a multi-field form.

## Catalog

| `catalog_id` | kind | Label | Cost |
|--------------|------|-------|-----:|
| `frame_bronze` | badge_frame | Bronze badge frame | 60 |
| `theme_aurora` | theme | Aurora theme | 80 |
| `flair_spark` | today_flair | Today spark flair | 90 |
| `title_pathfinder` | title | Title: Pathfinder | 100 |
| `theme_ember` | theme | Ember theme | 120 |
| `frame_silver` | badge_frame | Silver badge frame | 140 |
| `title_steady` | title | Title: Steady Hand | 150 |
| `title_finisher` | title | Title: Finisher | 250 |

Retired IRL ids (history only): `break_15`, `snack`, `media_ep`, `hobby_hour`, `meal_out`, `half_day`.

## Redeem rules

1. If `user.total_points < cost` → **HTTP 400**. No row written; balance unchanged.
2. Else subtract `cost`, insert `redemptions` row.
3. Unknown / DIY ids → rejected.

## Out of scope

IRL vouchers, DIY catalog, RNG loot, Settings theme pages, form sprawl on Wear.
