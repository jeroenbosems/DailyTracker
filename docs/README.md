# Documentation — source of truth

**Chat is not requirements.** Product decisions are only authoritative when written here and merged through GitFlow onto `main`.

| Doc | Purpose |
|-----|---------|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | Normative MUST / SHOULD requirements (versioned) |
| [PRODUCT.md](./PRODUCT.md) | Product vision, ontology, naming, roadmap |
| [ACCEPTANCE.md](./ACCEPTANCE.md) | Tester gates per release |
| [DECISIONS.md](./DECISIONS.md) | Decision log (what changed and why) |
| [GITFLOW.md](./GITFLOW.md) | Long-lived `dev` / `test` / `release` / `main` branch flow |
| [MOTIVATION.md](./MOTIVATION.md) | Design research / inspiration (non-normative) |
| [LLM_INGEST.md](./LLM_INGEST.md) | AI-assisted Epic authoring contract (New vs Update) |
| [templates/](./templates/) | Starter Epic JSON payloads (`mode:new`) for v0.4 |
| [REWARD_SHOP.md](./REWARD_SHOP.md) | Fixed reward shop catalog + redeem rules (v0.5) |
| [FOLLOW_ON.md](./FOLLOW_ON.md) | Follow-on Epic after completion (v0.6) |
| [EXPORT_BACKUP.md](./EXPORT_BACKUP.md) | JSON export / restore (v0.7) |

## Process

1. PO updates these docs when vision or scope changes.
2. Developer implements against **REQUIREMENTS.md** + **ACCEPTANCE.md**, not group chat. Feature PRs target **`dev`**.
3. Tester gates on **`test`** against **ACCEPTANCE.md** (see [GITFLOW.md](./GITFLOW.md)).
4. Ship path: `dev` → `test` (CLEAR) → `release` → `main`.
5. If chat and docs disagree, **docs win** until PO revises docs.
