# Reward shop — fixed catalog

**Status:** normative for v0.5  
**Tone:** adult productivity — real breaks and treats earned by useful work, not a DIY game economy.

## Principles

1. **Fixed catalog only** — prices and items are a code constant. No user-defined rewards or prices (see R3.4).
2. **Earn then spend** — points come from Priority rewards and Period bonuses; the shop only spends.
3. **Today stays focused** — Shop lives on `/shop`. Today’s point balance links to the shop; there is **no** shop section above Due now / Active Epic (R7.1).
4. **IRL follow-through** — redeeming spends points; “Done in real life” is a separate toggle when you actually take the break or treat.

## Catalog

| `catalog_id` | Label | Cost (pts) |
|--------------|-------|------------:|
| `break_15` | Short break (15 min) | 40 |
| `snack` | Favorite drink / snack | 80 |
| `media_ep` | Guilt-free media episode | 100 |
| `hobby_hour` | Hobby hour | 150 |
| `meal_out` | Nice meal out / takeaway | 300 |
| `half_day` | Half-day off project | 500 |

## Data

**`redemptions`**

| Field | Meaning |
|-------|---------|
| `user_id` | Owner |
| `catalog_id` | Key from the table above |
| `points_spent` | Cost at redeem time |
| `created_at` | When redeemed |
| `fulfilled_irl` | User marked the reward taken in real life |

## Redeem rules

1. If `user.total_points < cost` → **HTTP 400** with a clear “not enough points” message. No row written; balance unchanged.
2. Else subtract `cost` from `total_points`, insert a `redemptions` row (`fulfilled_irl=false`).
3. Optional `RewardLog` on spend is not required — spend is not an earn event.

## Out of scope

RNG loot, user-defined rewards/prices, shop chrome on the Today board above Due now / Active Epic.
