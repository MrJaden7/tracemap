# ADR 0011: Mapping coverage reporting

- Status: Accepted
- Date: 2026-11-04

## Context

The Phase 1 acceptance criteria require a "coverage report produced, with mapping coverage per domain reported in the README". Headline numbers also feature in the CV bullets if the project is cited.

## Decision

`tracemap coverage` writes two tables and prints a summary:

- `etl_meta.mapping_coverage`: per-run, per-source, per-domain: total_rows, mapped_rows, row_coverage_pct, distinct_codes, mapped_codes, code_coverage_pct.
- `etl_meta.unmapped_codes`: per-run, per-source, per-domain, per-code: row_count. Capped at 50 rows per run so the table does not grow unboundedly, and used to produce a "top unmapped codes" list for docs.

Row coverage and code coverage are both reported because they answer different questions:
- *row coverage*: what fraction of patient records can be analysed by domain? This drives research quality claims.
- *code coverage*: what fraction of distinct codes have been mapped? This drives where to spend mapping effort.

A low code coverage with high row coverage is a signal that a long tail of rare codes is unmapped. The reverse (high code coverage, low row coverage) means a few common codes are missing.

## Alternatives considered

- **Row coverage only.** Simpler, but hides the code tail.
- **Coverage per source vocabulary instead of per CDM domain.** Would obscure the mapping actually used; two vocabularies can feed the same domain.
- **Computed at dbt run time via a model.** Possible but `tracemap coverage` needs to run after `dbt test` anyway, and keeping it in Python lets us vary the metric set per run.

## Consequences

- The README shows real coverage numbers rather than a prose promise.
- Phase 2 will add a "coverage trend" page so each release is comparable.

## In plain English

Every build writes down what fraction of rows and what fraction of distinct codes were successfully mapped per CDM domain, with the unmapped codes to work on next.
