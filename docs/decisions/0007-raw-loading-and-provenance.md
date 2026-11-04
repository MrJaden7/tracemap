# ADR 0007: Raw loading, run tracking and provenance

- Status: Accepted
- Date: 2026-11-04

## Context

Row-level provenance is the most-persuasive feature of the project. For `tracemap trace condition_occurrence 12345` to work, every CDM row has to point back to an exact source file, an exact row inside it, and the ETL run that produced it. The spec also requires a changed input file to be detectable from its checksum, and a full rebuild to be idempotent.

## Decision

Everything source-related is captured at raw load time:

1. **One run record per end-to-end build**, in `etl_meta.cdm_run`, with `run_id`, started_at, finished_at, git commit, Synthea version, Synthea seed, Synthea jar SHA-256, vocabulary version, mapping spec version and status. The status moves from `running` to `completed` or `failed`.
2. **One raw table per CSV**, named `raw.synthea_<file>`. Columns come from the CSV header as `text` (every column nullable), plus two system columns:
   - `_source_row bigint NOT NULL`: 1-based row number inside the file.
   - `_run_id bigint NOT NULL`: the run that loaded the row.
   These let any CDM row point back with (`source_table`, `_source_row`) and the file checksum from the same run.
3. **One manifest row per file loaded**, in `raw.load_manifest`: run_id, source_system, target_table, file_name, file_path, file_sha256, file_size_bytes, row_count, loaded_at.
4. **Each file is truncated before being loaded**, and the loaded row count is compared with the data row count of the source file. Any mismatch stops the load and marks the run `failed`.
5. **Columns reserved by the loader (`_source_row`, `_run_id`) are refused** if present in a source CSV header, so a future source cannot collide with the provenance scheme.
6. **Load uses Postgres `COPY` into a temporary table**, then inserts into the real table with the two extra columns populated. Same reason as for vocabulary: `COPY` is orders of magnitude faster than row-by-row inserts.

Idempotence follows: because each table is truncated and the CSV has not changed (the checksum proves it), the second load produces the same rows, with the same `_source_row` values.

## Alternatives considered

- **One `raw.source_rows` table with a JSONB blob per row.** Flexible, but CSVs are tabular and the raw tables are easier to inspect this way.
- **Make `_source_row` the primary key.** Rejected: Synthea's `conditions.csv` has no natural key and uses position implicitly. A surrogate `_row_id` column adds no information `_source_row` doesn't already give.
- **No `_run_id` on raw rows, only in the manifest.** Rejected: the row then forgets which run put it there once the manifest is pruned. The current design lets any raw row identify its run directly.
- **Append-only raw loads with a `valid_from/valid_to`:** full historical fidelity but much more complex, and not needed because all source files are reproducible from Synthea with the same seed.

## Consequences

- Every raw row can be traced to the exact file, line and run.
- A changed source file is caught by a checksum change at load time.
- Reloading the same unchanged files gives identical raw rows, which is what the Phase 1 idempotence test needs.

## In plain English

Every synthetic CSV is loaded into a dedicated table, and each row records which line of which file it came from and which run of the pipeline brought it in. A checksum of every file is stored so anyone can prove the data has not been tampered with.
