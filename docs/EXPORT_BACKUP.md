# Export & backup (v0.7)

## Export

- Authenticated download from **Settings** → `GET /settings/export.json`
- Payload: `schema_version` (currently `1`), `exported_at`, `user` (username, total_points, active_epic_external_id — **no** password_hash), `tasks`, `routines`, `epics` (nested phases/steps), `reward_logs`, `redemptions`
- Entities get stable `external_id` values (minted on export if missing)

## Restore

- Upload on Settings → `POST /settings/restore`
- **merge**: create missing by `external_id`; never overwrite completed Steps
- **replace**: wipe product data for the user (keep login), then import; requires typing `REPLACE` and checking the confirm box
- Unknown `schema_version` → HTTP 400

## Out of scope

Cloud sync; writing auto-backups outside the Docker volume.
