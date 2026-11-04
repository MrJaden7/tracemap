# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-11-04

First release. Phases 1, 2 and 3 of the project brief implemented end to end.

### Added

- Monorepo layout (src/ Python package, dbt/, mapping_spec/, docs/, r/, analysis/).
- PostgreSQL 16 in Docker on host port 5440 with `shm_size: 1gb`.
- Official OHDSI CDM v5.4 PostgreSQL DDL, routed to `cdm` and `vocab` schemas at apply time.
- Vocabulary loader (`tracemap vocab load`) with row-count verification and index build.
- Verified concept constants: 7 hard-coded concept IDs, each asserted against the loaded vocabulary.
- Em-dash style gate as a unit test.
- Synthea runner pinned to v3.3.0 seed 42; jar fetched with SHA-256 verification.
- Raw loader with SHA-256 per file, `_source_row` and `_run_id` on every row, `raw.load_manifest`.
- Mapping specification (`mapping_spec/*.yml`) with 11 rule types in a strict pydantic schema; `tracemap spec check`.
- Generator for dbt SQL models, dbt schema tests, markdown mapping docs, per-table and whole-project Mermaid lineage diagrams; MkDocs Material site scaffold.
- 14 Phase 1 CDM tables populated end-to-end (person, observation_period, visit, condition, drug, procedure, measurement, observation, death, location, care_site, provider, cdm_source, metadata).
- condition_era, drug_era using the standard 30-day gap rule.
- `tracemap trace <cdm_table> <id>` walking any CDM row back to its exact source.
- `tracemap coverage` report and `etl_meta.mapping_coverage`, `etl_meta.unmapped_codes`.
- Three cohort queries (t2dm_hba1c, hypertension_incidence, ed_to_admission) run via `tracemap analysis`, output checker with small-number suppression.
- UK synthetic hospital extract (ICD-10, OPCS-4) with HMAC-SHA256 pseudonymised linkage to Synthea; multi-source UNION in person and condition_occurrence.
- `normalise_icd10` / `normalise_opcs4` dbt macros.
- OHDSI Data Quality Dashboard runner (`r/run_dqd.R`) and ETL-Synthea reconciliation runner (`r/run_etl_synthea.R`) with run instructions.
- Fixture vocabulary for CI (`tests/fixtures/vocab/`) and GitHub Actions workflow.
- AI mapping evaluation module (Phase 3): 300-item mappable gold set + 50 unmappable, 4 methods (exact, BM25, hybrid, LLM re-ranker), hard safety gate, repeated runs with mean +/- stdev.
- 13 ADRs covering every substantial design decision.
- Idempotence test skeleton.

### Numbers

- 34 unit tests, 8 integration tests, 70 dbt tests, all green.
- CDM: 7.3 million rows across 14 tables.
- AI mapping: BM25 reaches 80.0 % top-1 accuracy at 95.4 % coverage; exact match reaches 99.2 % precision at 34.3 % coverage.
