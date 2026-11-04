# Data quality

TraceMap's quality evidence has three layers:

## dbt tests

- 70 tests covering `not_null` and `unique` constraints on every column the OMOP CDM v5.4 DDL marks NOT NULL or primary key.
- Generated from the specs by `tracemap generate`.
- Full test output is committed in each release's `dbt_test_results.txt`.

## Custom SQL checks

In `dbt/tests/singular/`:

- Every event date falls within the person's `observation_period`.
- No events after `death.death_date` beyond a documented small tolerance.
- `start_date <= end_date` on every event table.
- `birth_datetime` before all events.
- Every non-zero `*_concept_id` exists in `vocab.concept`.

## OHDSI Data Quality Dashboard

The DQD (`r/run_dqd.R`) runs against the `cdm` + `vocab` schemas and produces a per-category pass rate (conformance, completeness, plausibility). Every failure is either fixed or explained in `docs/data_quality.md`.

The DQD is an R tool, so it is not part of the Python integration tests. The R script and its run instructions are committed; results are captured in `docs/dqd/` after each release.

## Mapping coverage

`tracemap coverage` writes two tables and reports the summary:

- `etl_meta.mapping_coverage`: per-run, per-source, per-domain row coverage and code coverage.
- `etl_meta.unmapped_codes`: the top unmapped codes, which drive the next iteration of mapping effort.

See [ADR 0011](decisions/0011-mapping-coverage.md) for the rationale.
