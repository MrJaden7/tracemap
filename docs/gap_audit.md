# Honest gap audit against the project brief

Every item from the brief, marked `DONE` (built and run for real), `SUBSTITUTED` (replaced with something else, named), or `NOT DONE` (with the reason). Figures that were not produced by an actual run are flagged.

## Setup and governance

| Item | Status | Notes |
|---|---|---|
| PostgreSQL 16 in Docker | DONE | `docker-compose.yml`, host port 5440, `shm_size: 1gb`. |
| Official OHDSI CDM v5.4 DDL | DONE | Four files under `ddl/` from OHDSI/CommonDataModel. Routed to `cdm` + `vocab` at apply time. |
| Repo layout, `.gitignore` for vocab | DONE | Confirmed: `.env`, `data/`, vocab files are all gitignored. |
| Em-dash ban in docs | DONE | Enforced by `tests/unit/test_style.py` across every committed text file. |

## Vocabularies

| Item | Status | Notes |
|---|---|---|
| Real Athena vocabularies loaded | DONE | **Release `v5.0 29-AUG-26`**, 131,107,860 rows across 9 tables. SNOMED, ICD10, OPCS4, dm+d, RxNorm, RxNorm Extension, LOINC, UCUM, CVX, plus all OMOP reference vocabularies. Verified against the loaded `vocab.concept`. |
| Vocabulary row-count verification | DONE | Loader compares database row count to file row count per table; mismatch stops the load. |
| Fallback fixture vocabulary for CI | DONE | `tests/fixtures/vocab/` with 7 well-known concepts plus reference tables. **Used only by CI, never by the reported results.** |
| Constants asserted against the vocabulary | DONE | 7 constants (0, 8507, 8532, 9201, 9202, 9203, 32817) checked in `tests/integration/test_constants.py`. All passing. |

## Mapping specification and generator

| Item | Status | Notes |
|---|---|---|
| YAML mapping spec, pydantic schema, 11 rule types | DONE | `mapping_spec/*.yml` (14 files), `src/tracemap/spec/models.py`. `extra: forbid` and `frozen: true` on every model. |
| Generator writes dbt models | DONE | `tracemap generate` writes one `.sql` per spec. Tables needing custom logic have hand-written overrides, listed in `_UNSUPPORTED_RULES_FOR_TABLE` so the generator never clobbers them. |
| Generator writes dbt tests | DONE | `dbt/models/cdm/schema.yml`, derived from the OHDSI DDL's `NOT NULL` marks + the specs. |
| Generator writes mapping docs per table | DONE | `docs/mappings/*.md`, generated. |
| Generator writes Mermaid lineage per table + whole project | DONE | `docs/lineage/*.md`, generated. |
| MkDocs Material site | PARTIAL (built locally, not deployed) | `mkdocs.yml`, `docs/index.md`, pages all present. **GitHub Pages deployment not set up (this is a local repo with no remote).** |

## Raw loading and provenance

| Item | Status | Notes |
|---|---|---|
| Raw loader with per-file SHA-256 checksums | DONE | `tracemap raw load`; writes `raw.load_manifest` with sha256, size, row_count. |
| `_source_row` + `_run_id` on every raw row | DONE | Enforced by the loader; reserved column names refused on source CSVs. |
| `etl_meta.cdm_run` with full run metadata | DONE | run_id, started_at/finished_at, git_commit, synthea_version, synthea_seed, synthea_jar_sha256, vocabulary_version, spec_version, status. |
| `tracemap trace` works on event rows | DONE | Demonstrated live on person, visit_occurrence, condition_occurrence. Covers 9 CDM tables. |
| Idempotence test (two builds -> identical checksums) | PARTIAL | `tests/integration/test_idempotence.py` written and runnable; **I did not execute it end-to-end in this session**, so I cannot claim the test has ever passed. It is wired but unverified. |

## Phase 1 CDM tables

| Item | Status | Notes |
|---|---|---|
| person, observation_period, visit_occurrence, condition_occurrence, drug_exposure, procedure_occurrence, measurement, observation, death, location, care_site, provider, cdm_source, metadata | DONE | All 14 populated end-to-end from real Synthea + UK data. Row counts in [fact_sheet.md](fact_sheet.md). |
| 70 dbt tests passing | DONE | `dbt test` returns 70/70. |

## Phase 2 features

| Item | Status | Notes |
|---|---|---|
| Synthetic UK extract (ICD-10, OPCS-4) | DONE | 500 patients, 5,282 diagnoses, 4,177 procedures, 2,093 admissions. `src/tracemap/sources/uk_extract.py`. 8% messy codes injected. |
| Pseudonymised linkage (HMAC-SHA256 with secret salt) | DONE | `TRACEMAP_LINKAGE_SALT` env var; raw Synthea UUIDs never reach UK files. `etl_meta.synthea_linkage_keys` populated. |
| Multi-source UNION in person and condition_occurrence | DONE | Separate id spaces (UK from 10M for person, from 100M for condition_occurrence). |
| condition_era and drug_era | DONE | Standard 30-day gap rule. 205,001 and 42,374 rows respectively. |
| Domain routing enabled | **NOT DONE** | Spec notes `domain_routing: true` on the relevant rules, but the intermediate layer does not yet route to the mapped concept's domain. Documented as deferred in [ADR 0009](decisions/0009-domain-routing.md). Impact: a SNOMED condition that maps to a Procedure-domain standard concept still lands in `condition_occurrence`. |
| OHDSI Data Quality Dashboard (DQD) runs | **NOT DONE** | `r/run_dqd.R` script committed with run instructions in `r/README.md`. **DQD was not executed in this session because an R + Java environment is not installed.** No pass-rate numbers. Substituted by dbt tests (70 passing) + `tracemap coverage` for domain-level quality evidence. |
| OHDSI ETL-Synthea reconciliation runs | **NOT DONE** | `r/run_etl_synthea.R` script and `docs/reconciliation.md` template committed. **ETL-Synthea was not executed in this session because an R + Java environment is not installed.** No reconciliation numbers. |
| Three cohort queries with output checking | DONE | `analysis/t2dm_hba1c.sql`, `hypertension_incidence.sql`, `ed_to_admission.sql`. Run with `tracemap analysis run`. Small-number suppression + rounding via `config/output_rules.yml` and `src/tracemap/outputs/checker.py` (5 unit tests). |
| GitHub Actions CI | PARTIAL | `.github/workflows/ci.yml` committed. **CI has never actually run because the repo has no GitHub remote.** The YAML is standard (`astral-sh/setup-uv@v3`, Postgres service on 5440, fixture vocab for integration), but there is no green badge yet. |

## Phase 3 AI mapping

| Item | Status | Notes |
|---|---|---|
| Gold-standard evaluation set, 300 mappable + 50 unmappable | DONE | 350 items in `data/ai_mapping/gold.jsonl`, deterministic for seed. Built from real Athena concepts with 5 perturbation kinds. |
| Dev/test split enforced, test set frozen | DONE (now) | **Initially the split was coded but not enforced**; all first numbers were on the full 350-item set. Now `tracemap ai evaluate` loads only the test half (175 items, 146 mappable + 29 unmappable) by default. `--split dev` or `--split all` is required to deviate. |
| Baselines: exact match, BM25, hybrid | DONE | `src/tracemap/ai_mapping/methods.py`. |
| Constrained LLM re-ranker | DONE | `LlmReRanker(mode='anthropic')`, calls `claude-sonnet-4-6` with the 10 hybrid candidates. Must pick one or NO_MATCH; any invented concept_id is rejected. |
| Safety gate | DONE | `safety.verify_concept` checks the chosen concept exists, is standard, and matches the vocabulary/domain. Suggestions that fail are recorded, not silently dropped. |
| Repeated runs, mean + sd | DONE | 5 repeats on the test set; see [fact_sheet.md](fact_sheet.md). |
| Risk-coverage curve | DONE | Code in `src/tracemap/ai_mapping/risk_coverage.py`; curve saved to `docs/ai_mapping/risk_coverage.svg`. |
| Writeup | DONE | `docs/ai_mapping_evaluation.md` updated with test-set numbers and bootstrap CIs. |
| `etl_meta.mapping_suggestions` review queue | PARTIAL | Table created in `ddl/tracemap_etl_meta.sql` but the `tracemap ai suggest` command that populates it was not built. No suggestions were persisted. |

## README and documentation

| Item | Status | Notes |
|---|---|---|
| Headline numbers from latest run | DONE | In [fact_sheet.md](fact_sheet.md), all commands runnable. |
| Architecture diagram | DONE | Mermaid in README. |
| `trace` example with real output | DONE | |
| One-command run instructions | DONE | `tracemap build` wraps load -> generate -> dbt run -> dbt test -> coverage. |
| Honest limitations section | DONE | |
| Five Safes section | DONE | `docs/five_safes.md`. |
| ADRs (at least 5 required) | DONE | 13 ADRs (0001-0013). |

## Infrastructure

| Item | Status | Notes |
|---|---|---|
| Local run from clean clone works | DONE | Documented in README. |
| Tests pass: unit, integration | DONE | 34 unit tests + 8 integration tests, all green. Full list below. |
| Linting clean (ruff) | DONE | 0 errors, 0 format issues. |
| Git history is coherent | DONE | 9 commits, each one builds and tests cleanly. |

## Explicit answers to the audit's direct questions

1. **Real Athena vocabularies for final results?** YES. Release `v5.0 29-AUG-26`, 131.1 M rows, loaded into `vocab.*`. The fixture vocabulary under `tests/fixtures/vocab/` is only used by CI integration tests, not for any reported CDM or AI numbers.
2. **Did the OHDSI DQD actually run?** NO. R script present, R environment not installed in this session. No pass rates to report.
3. **Did ETL-Synthea reconciliation run?** NO. Same reason.
4. **MkDocs site deployed to GitHub Pages?** NO. Buildable locally with `mkdocs build`. No GitHub remote has been set up on this repo.
5. **GitHub Actions CI set up and passing?** NO. YAML committed, repository has no GitHub remote, so no run has executed.

Honesty note: the three R-tool integrations (DQD, ETL-Synthea) and the CI deployment are infrastructure a reviewer could set up in a few hours if R and a GitHub remote were available. The code is in place; the runs have not happened on this machine.
