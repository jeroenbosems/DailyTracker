# GitFlow (Daily Tracker)

Long-lived branches (all exist on origin):

| Branch | Role |
|--------|------|
| `dev` | Integration — feature work lands here first |
| `test` | Acceptance — Tester gates here |
| `release` | Release candidate — stabilize only |
| `main` | Production / real-use tip |

## Day-to-day

```
feat/* ──PR──▶ dev ──PR──▶ test ──CLEAR──PR──▶ release ──PR──▶ main
                 ▲                                    │
 hotfix/* ──PR───┴────────── (from main) ─────────────┘
                 └── then back-merge hotfix into release + dev
```

1. **Developer:** branch `feat/…` or `fix/…` from latest `dev`. Open PR **into `dev`**. Self-check / pytest green before asking for promote.
2. **Promote to test:** when the slice matches locked ACCEPTANCE, open PR **`dev` → `test`**. @Daily Tracker Tester gates.
3. **CLEAR → release:** open PR **`test` → `release`**. No new product scope on `release`.
4. **Ship:** open PR **`release` → `main`**. Tag/version notes as needed.
5. **Hotfix:** `hotfix/…` from `main` → PR into `main`, then merge the same fix into `release` and `dev`.

## Rules

- Do not push product code straight to `main`.
- Tester **CLEAR** is required before `test` → `release`.
- Chat is not the contract — decisions live in `docs/` (see DECISIONS.md).
- Stale feature branches may be deleted after merge; long-lived four stay.
