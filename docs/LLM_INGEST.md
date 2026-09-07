# LLM ingest contract

**Status:** implemented for v0.3  
**Normative rules:** REQUIREMENTS R8.*  
**UI:** `/import` (paste JSON → New or Update)

## Intent

User describes a project to any LLM → model emits JSON matching this schema → user imports into Daily Tracker.

## Modes

| Mode | Behavior |
|------|----------|
| `new` | Create Epic + Phases + Steps. No prior progress. Stores optional `id` values as `external_id`. |
| `update` | Patch by stable `id`s (`external_id`). **Must not** silently delete completed Steps or reset Phase/Epic completion. |

Destructive updates (remove existing Steps/Phases, including in-progress or completed) require **both**:

1. `confirm_destructive: true` in the JSON, and  
2. the Import page confirmation checkbox.

## Schema

Stable string ids use the `id` fields below; the app stores them as `external_id` for update matching.

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

### Field notes

| Field | Meaning |
|-------|---------|
| `mode` | `new` or `update` |
| `confirm_destructive` | Required `true` (with UI checkbox) to remove existing Steps/Phases on update |
| `epic.id` | Stable external id (required for `update`) |
| `epic.status` | Optional `active` \| `parked` — `active` sets Active Epic; first Epic also activates when none is Active |
| `phases[].id` / `steps[].id` | Stable external ids for matching on update |
| `order` | Sort order (integer) |
| `priority` | Step priority 1–3 |

## LLM system prompt (short)

You break a user's real-life ambitious project into Daily Tracker JSON: one Epic, ordered Phases (week-scale), Steps (day-scale). Prefer high-value Steps over busywork. Include identity, capability, preview, and per-Phase deliverable. Output **only** JSON matching the schema. For revisions, use `mode: update` with existing ids; never remove completed work unless the user explicitly asks and you set `confirm_destructive: true`.

## v0.3.2 path

Optional epic.path: full (default) or focused. Focused plans should use fewer condensed Phases.
