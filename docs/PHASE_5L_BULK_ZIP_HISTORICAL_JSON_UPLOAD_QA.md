# Phase 5L Manual QA — Bulk ZIP Historical JSON Upload

## ZIP safety rules
- Endpoint accepts `.zip` only (`POST /api/historical-import/json/bulk-zip/dry-run` and `/bulk-zip/apply`).
- Unsafe ZIP entry paths are rejected (absolute paths, `..` traversal, Windows drive paths).
- Limits enforced:
  - max files: `100`
  - max per-file size: `2 MB`
  - max total uncompressed size: `20 MB`
  - max total compressed size: `20 MB`

## File handling behavior
- Only `.json` entries are processed.
- Non-JSON entries are reported as `unsupported`.
- Each JSON is dry-run validated independently.
- One invalid JSON does not block other valid JSON previews.

## Duplicate handling
- Duplicates are detected within ZIP (hash or semantic-key repeats).
- Duplicates are detected against existing import batches (hash or semantic key).
- Duplicate files are marked `duplicate` and are not eligible for safe apply.

## Per-file status meanings
- `valid`: safe dry-run preview exists and no duplicate signal.
- `invalid`: JSON parse/validation failed.
- `duplicate`: duplicate found within ZIP or against existing batch records.
- `unsupported`: non-JSON entry or unsupported JSON shape.
- `error`: unexpected processing failure.

Apply statuses:
- `applied`: selected file recorded + applied through existing single-file pipeline.
- `skipped`: selected file not valid/safe for apply.
- `error`: selected file apply failed.

## Manual QA checklist
- [ ] Upload ZIP with multiple valid JSON files → all preview as `valid`.
- [ ] Upload non-ZIP payload → request fails with clear 415 error.
- [ ] Upload ZIP containing unsafe path (`../x.json`) → request rejected.
- [ ] Upload ZIP containing JSON + non-JSON files → non-JSON shown as `unsupported`.
- [ ] Upload ZIP with repeated JSON content → second file marked `duplicate`.
- [ ] Record one single-file import, then preview ZIP with same JSON → file marked duplicate against existing batch.
- [ ] Upload ZIP with one invalid JSON + one valid JSON → valid preview still available.
- [ ] Call `/bulk-zip/apply` with `confirm=false` → rejected (422), no batch finalized.
- [ ] Call `/bulk-zip/apply` with selected valid + invalid files and `confirm=true` → only valid file applied.
- [ ] Verify Analyst/live scoring truth remains untouched (no live/in-progress mutation).

## Phase 5M registry readiness notes
- Raw ZIP bytes and raw JSON are not retained server-side in Phase 5L.
- Existing batch metadata (`source_hash_sha256`, semantic key, dry-run summary) remains the audit foundation.
- Phase 5M can build registry/index workflows on finalized batch metadata without schema changes in this phase.
