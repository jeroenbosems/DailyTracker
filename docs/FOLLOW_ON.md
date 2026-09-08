# Follow-on Epic (v0.6)

## Intent

After an Epic completes, the user can explicitly start a **follow-on** Epic to refine / maintain — never automatic.

## Rules

- CTA only on completed Epics (detail + Today celebration).
- New row in `epics` with `follows_epic_id` → completed Epic id.
- Completed Epic is not mutated (title, phases, completion, identity, etc. stay).
- Prefill is editable before save; default path **Focused**; starter Phases Stabilize / Improve.
- UI: “Follows: …” on the new Epic; “Follow-ons” on the completed one.
