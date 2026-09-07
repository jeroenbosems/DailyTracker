# LLM ingest contract

**Status:** stub for v0.3 (schema stable enough to draft prompts now)  
**Normative rules:** REQUIREMENTS R8.*

## Intent

User describes a project to any LLM → model emits JSON matching this schema → user imports into Daily Tracker.

## Modes

| Mode | Behavior |
|------|----------|
| `new` | Create Epic + Phases + Steps. No prior progress. |
| `update` | Patch by stable `id`s. **Must not** silently delete completed Steps or reset Phase/Epic completion. |

Destructive updates (remove/replace in-progress Steps) require `confirm_destructive: true`.

## Schema (draft)

```json
{
  "mode": "new",
  "confirm_destructive": false,
  "epic": {
    "id": "epic_optional_for_update",
    "title": "Redo the apartment",
    "identity": "Someone who finished a calm, usable home base",
    "capability": "Live and work in a finished apartment without renovation hanging over me",
    "preview": "One corner of the living room fully done and usable",
    "status": "active",
    "phases": [
      {
        "id": "phase_1",
        "title": "Plan & declutter",
        "order": 1,
        "deliverable": "Room-by-room plan + donate/sell bags staged",
        "steps": [
          {
            "id": "step_1",
            "title": "Photograph each room",
            "order": 1,
            "parallel": true,
            "priority": 1
          }
        ]
      }
    ]
  }
}
```

## LLM system prompt (short)

You break a user's real-life ambitious project into Daily Tracker JSON: one Epic, ordered Phases (week-scale), Steps (day-scale). Prefer high-value Steps over busywork. Include identity, capability, preview, and per-Phase deliverable. Output **only** JSON matching the schema. For revisions, use `mode: update` with existing ids; never remove completed work unless the user explicitly asks and you set `confirm_destructive: true`.
