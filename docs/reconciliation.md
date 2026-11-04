# Reconciliation against ETL-Synthea

TraceMap is compared against OHDSI's reference ETL (ETL-Synthea v2.1.1) on the same Synthea output. The reference builds into the `reference_etl` schema; TraceMap builds into `cdm`. This page records the differences and their explanation.

## Method

1. `tracemap build` produces `cdm.*`.
2. `Rscript r/run_etl_synthea.R` produces `reference_etl.*` from the same Synthea CSVs.
3. The comparison SQL in `analysis/reconcile.sql` runs: per-table row counts, per-domain top concept distributions.

## Differences expected by design

| Observation | Explanation |
|---|---|
| `cdm.person` is larger | TraceMap also loads the UK synthetic extract. Filter to `source_system = 'synthea'` in the comparison. |
| `cdm.condition_occurrence` is larger | Same reason. |
| Era tables may differ slightly | TraceMap uses the 30-day gap rule verbatim; ETL-Synthea may use a slightly different grouping on edge cases. Documented in ADR 0012 (Phase 2 close-out). |
| Death row counts match | Both ETLs filter to non-null deathdate. |
| Vocabulary version matches | Both run against the same loaded vocabularies. |

## Differences to investigate

Not yet observed. Each new difference is added here with a one-sentence reason or a bug issue.

## Run metadata

Populate on each reconciliation run:

- TraceMap run_id:
- ETL-Synthea version:
- Synthea version and seed:
- Vocabulary version:
- Date of comparison:
