# ADR 0004: How vocabularies are loaded and verified

- Status: Accepted
- Date: 2026-11-04

## Context

The Athena download is about 5 GB across 12 files. The two largest are `CONCEPT_RELATIONSHIP` (2.1 GB) and `CONCEPT_ANCESTOR` (1.7 GB). The files are tab-separated despite the `.csv` extension, and concept names can contain double quotes.

## Decision

`tracemap vocab load` (`src/tracemap/load/vocab.py`):

1. **Checks first.** Every expected file and every required vocabulary must be present (see ADR 0003).
2. **Loads with Postgres `COPY`**, streamed in 8 MB chunks, with tab as the delimiter and a backspace character as the quote character. Backspace never appears in the data, so double quotes in concept names are kept as literal text instead of being treated as quoting.
3. **Verifies row counts.** After each table is loaded, the database row count is compared with the number of data lines in the source file. Any difference stops the load.
4. **Builds indexes after loading**, because maintaining indexes during a bulk load is much slower. It uses OHDSI's vocabulary indexes plus two composite indexes for the lookups the mapping SQL performs: `concept (concept_code, vocabulary_id)` and `concept_relationship (concept_id_1, relationship_id)`.
5. **Skips OHDSI's `CLUSTER` statements.** `CLUSTER` physically reorders a table on disk. It does not change any query result and takes a long time on multi-gigabyte tables. It can be turned on later if query speed needs it.
6. **Records the load** in `etl_meta.vocabulary_load`: table, file, file rows, loaded rows, release, timestamp.
7. **Skips three files**, `CONCEPT_METADATA`, `CONCEPT_RELATIONSHIP_METADATA` and `PACK_CONTENT`. Athena ships them, but they are not part of the CDM v5.4 DDL.

Each table is truncated before loading, so running the load twice gives the same result.

## Alternatives considered

- **pandas `to_sql`:** familiar, but loads row by row through Python and would take hours for 5 GB.
- **OHDSI's R loaders:** work, but add R as a Phase 1 dependency. R is only needed in Phase 2.
- **Skipping the row-count check:** faster, but a silently truncated load (for example from a malformed line) would go unnoticed and produce wrong mappings later.

## Consequences

- A full load takes several minutes rather than hours.
- A corrupted or partial download is caught at load time, not discovered later as missing mappings.

## In plain English

The vocabulary files are loaded with the database's fastest bulk-load method, and every table is counted afterwards to prove nothing was lost on the way in.
