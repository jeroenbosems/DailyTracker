# Documentation — source of truth

**Chat is not requirements.** Product decisions are only authoritative when written here and merged to `main`.

| Doc | Purpose |
|-----|---------|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | Normative MUST / SHOULD requirements (versioned) |
| [PRODUCT.md](./PRODUCT.md) | Product vision, ontology, naming, roadmap |
| [ACCEPTANCE.md](./ACCEPTANCE.md) | Tester gates per release |
| [DECISIONS.md](./DECISIONS.md) | Decision log (what changed and why) |
| [MOTIVATION.md](./MOTIVATION.md) | Design research / inspiration (non-normative) |
| [LLM_INGEST.md](./LLM_INGEST.md) | AI-assisted Epic authoring contract (New vs Update) |

## Process

1. PO updates these docs when vision or scope changes.
2. Developer implements against **REQUIREMENTS.md** + **ACCEPTANCE.md**, not group chat.
3. Tester gates releases against **ACCEPTANCE.md**.
4. If chat and docs disagree, **docs win** until PO revises docs.
