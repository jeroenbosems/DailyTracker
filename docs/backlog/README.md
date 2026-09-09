# Product backlog (in-repo)

Replaces Jira / Azure DevOps / Trello for this project. **Chat is not the backlog.**

## Workflow statuses

| Status | Meaning | Owner |
|--------|---------|--------|
| `planned` | Refined enough to estimate; not started | PO |
| `doing` | Actively being built on a `feat/*` branch | Developer |
| `ready_for_test` | On `dev`, waiting promote/`test` gate | Developer → Tester |
| `tested` | Tester CLEAR on `test` | Tester |
| `committed` | Merged through GitFlow onto `main` (shipped) | Developer |

## Rules

1. PO owns prioritization (`priority` ascending = do sooner) and refinement.
2. Developer estimates **time-to-get-it-right** (solid shippable quality, not a throwaway spike) in `estimate` once `refined: true`.
3. Tester **pushes back** when an item doesn’t match the codebase, NFRs, or product direction — escalate to PO; PO may cut or re-scope.
4. Only `planned` / `doing` / `ready_for_test` items are “open work.” `committed` is history.
5. Feature freeze (e.g. post `v1.0-rc`) means no new `doing` except bugfixes (`type: bug`) until PO reopens.

## Files

- [`items.yaml`](./items.yaml) — source of truth for all backlog items
- This README — process

## GitFlow

Item work still follows `feat/*` → `dev` → `test` → `release` → `main`. Update `status` in the same PR that moves the work, when practical.
