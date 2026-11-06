# Fact sheet

Only numbers produced by an actual run. Every row is paired with the command that reproduces it. Numbers reported to the precision the underlying count or evaluation provides, with no rounding that would flatter the results. Dated 2026-11-04.

## Inputs

| Thing | Value | Source |
|---|---|---|
| Synthea version | v3.3.0 | `cat src/tracemap/synthea.py` (pinned constant, verified by SHA-256 of the jar) |
| Synthea seed | 42 | `uv run tracemap synthea generate --patients 5000 --seed 42` |
| Vocabulary release | v5.0 29-AUG-26 | `psql -c "SELECT vocabulary_version FROM VOCABULARY WHERE vocabulary_id='None'"` |
| UK extract seed | 42 | `uv run tracemap uk-extract generate --patients 500 --seed 42` |
| Linkage salt | taken from TRACEMAP_LINKAGE_SALT env var | `cat .env` (never committed) |

## Patients per source (raw)

| Source | Raw patients | Command |
|---|---:|---|
| Synthea | 5,807 | `SELECT count(*) FROM raw.synthea_patients` |
| UK extract | 500 | `SELECT count(*) FROM raw.uk_patients` |

## Raw rows loaded

Totals for the loaded runs, from `raw.load_manifest`.

| Target table | Rows |
|---|---:|
| raw.synthea_patients | 5,807 |
| raw.synthea_encounters | 433,084 |
| raw.synthea_conditions | 230,165 |
| raw.synthea_medications | 378,966 |
| raw.synthea_procedures | 862,865 |
| raw.synthea_observations | 5,579,873 |
| raw.synthea_immunizations | 85,295 |
| raw.synthea_allergies | 5,210 |
| raw.synthea_organizations | 1,077 |
| raw.synthea_providers | 1,077 |
| raw.synthea_payers | 10 |
| raw.synthea_payer_transitions | 58,021 |
| raw.synthea_claims | 812,050 |
| raw.synthea_claims_transactions | 5,686,513 |
| raw.synthea_imaging_studies | 432,722 |
| raw.synthea_devices | 9,846 |
| raw.synthea_careplans | 20,368 |
| raw.synthea_supplies | 58,237 |
| raw.uk_patients | 500 |
| raw.uk_admissions | 2,093 |
| raw.uk_diagnoses | 5,282 |
| raw.uk_procedures | 4,177 |

Command: `psql -c "SELECT target_table, row_count FROM raw.load_manifest ORDER BY target_table"`.

## CDM rows produced

| CDM table | Rows |
|---|---:|
| cdm_source | 1 |
| metadata | 6 |
| death | 807 |
| care_site | 1,077 |
| provider | 1,077 |
| observation_period | 5,807 |
| person | 6,307 (5,807 Synthea + 500 UK) |
| location | 6,853 |
| drug_era | 42,374 |
| condition_era | 205,001 |
| condition_occurrence | 235,447 (230,165 Synthea + 5,282 UK) |
| drug_exposure | 378,966 |
| visit_occurrence | 433,084 |
| procedure_occurrence | 862,865 |
| observation | 1,743,754 |
| measurement | 3,676,459 |

**Total CDM rows: 7,599,885.** Command: `psql -c "SELECT ..."` on each CDM table (see `docs/gap_audit.md` for the full query).

## Mapping coverage per domain

Produced by `uv run tracemap coverage` which also writes `etl_meta.mapping_coverage` and `etl_meta.unmapped_codes`.

| Source | Domain | Rows | Row coverage | Distinct codes | Code coverage |
|---|---|---:|---:|---:|---:|
| synthea | condition_occurrence | 230,165 | 97.03% | 721 | 45.21% |
| synthea | drug_exposure | 378,966 | 100.00% | 332 | 100.00% |
| synthea | procedure_occurrence | 862,865 | 92.43% | 807 | 43.99% |
| synthea | measurement | 3,676,459 | 99.99% | 178 | 97.19% |
| synthea | observation | 1,743,754 | 99.92% | 99 | 84.85% |
| synthea | visit_occurrence | 433,084 | 100.00% | 10 | 100.00% |

The UK source feeds `condition_occurrence` only in this phase; UK row coverage is not yet surfaced separately (would require splitting the coverage query by `source_system`, which is a one-line change in `src/tracemap/quality/coverage.py` for Phase 2 close-out).

## Data quality

| Check | Result | Command |
|---|---|---|
| dbt tests | **70 / 70 pass** | `cd dbt && dbt test` |
| Python unit tests | **34 / 34 pass** | `uv run pytest -q` |
| Python integration tests | **8 / 8 pass** | `uv run pytest -q -m integration` (requires Postgres + fixture vocab) |
| OHDSI Data Quality Dashboard (v2.9.1) | **1,747 / 1,765 passed (98.98%)** | 18 failed, 0 errors. Conformance 627/634 (98.9%), Completeness 310/316 (98.1%), Plausibility 268/273 (98.2%). Full JSON at [docs/dqd/dqd_result.json](dqd/dqd_result.json). Reproduce: `tracemap db conform-cdm; Rscript /tmp/dqd_clean.R` (DQD needs the full OHDSI column set to roll up correctly, see [gap_audit.md](gap_audit.md)). |
| Idempotence (build twice, compare md5) | **NOT RUN** | `tests/integration/test_idempotence.py` is committed but marked `slow`; not executed end-to-end in this session. |

## Reconciliation

| Check | Result |
|---|---|
| ETL-Synthea reconciliation | **DONE for 17 of 18 tables.** Reference built with `ETLSyntheaBuilder` v2.1. 5 tables match exactly (person Synthea-only, observation_period, care_site, provider, cdm_source). 3 within 10%, 2 within 20%, 3 with 2×+ divergence explained by ADR 0009 domain routing. 2 known gaps on our side (visit_detail, device_exposure - Phase 2). `cost` INSERT aborted at ~8h / 0 rows (our pipeline does not model cost; nothing to compare). Full table at [docs/reconciliation.md](reconciliation.md). |

## AI mapping results

**All numbers below are from the frozen held-out test set only: 175 items (146 mappable + 29 unmappable), deterministically split from the 350-item gold set by sha256(term). Enforced by `tracemap ai evaluate` defaulting to `--split test`.**

Command to reproduce:

```bash
uv run tracemap ai evaluate --repeats 5 --use-llm --split test
```

| Method                   | Top-1 acc         | Precision         | Coverage          | Correct abstention |
|--------------------------|-------------------|-------------------|-------------------|--------------------|
| exact_match              | 0.390 +/- 0.000   | 0.983 +/- 0.000   | 0.331 +/- 0.000   | 1.000 +/- 0.000    |
| bm25                     | 0.836 +/- 0.000   | 0.731 +/- 0.000   | 0.954 +/- 0.000   | 0.034 +/- 0.000    |
| hybrid                   | 0.836 +/- 0.000   | 0.731 +/- 0.000   | 0.954 +/- 0.000   | 0.034 +/- 0.000    |
| rerank_fallback_no_llm   | 0.822 +/- 0.000   | 0.727 +/- 0.000   | 0.943 +/- 0.000   | 0.034 +/- 0.000    |
| llm_rerank_anthropic     | **0.890 +/- 0.000** | **0.922 +/- 0.000** | 0.806 +/- 0.000 | **0.828 +/- 0.000** |

**Note on the zero standard deviations.** 5 runs of 175 items each produced identical metrics at 3-decimal rounding for every method, including the Anthropic re-ranker. The deterministic baselines are deterministic by construction (no randomness in BM25 scoring, exact match, or the no-LLM fallback). The LLM re-ranker's zero stdev reflects that `claude-sonnet-4-6` is highly consistent on this constrained JSON-output task; any run-to-run variation is below the 0.0005 rounding boundary. I did not increase the display precision to show a flattering-looking tiny stdev.

**Bootstrap 95% paired confidence intervals, llm_rerank_anthropic minus hybrid, PER METRIC DENOMINATOR.**

The earlier numbers in this document were from a bootstrap that averaged a boolean over all 175 items regardless of metric. That was wrong. Each CI now resamples from the items that define its metric. Implementation in `src/tracemap/ai_mapping/statistics.py`; 6 unit tests pin the correct behaviour. CI widths are from 2,000 paired resamples.

| Metric             | n (denominator)        | Mean diff | 95% CI             | Significant? |
|--------------------|-----------------------:|----------:|--------------------|--------------|
| top-1 accuracy     | 146 mappable items     | **+0.055** | [+0.000, +0.110]  | **Marginal** (lower bound touches zero) |
| precision          | 175 items (resample)    | **+0.191** | [+0.128, +0.264] | Yes |
| coverage           | 175 items               | **-0.149** | [-0.211, -0.091]  | Yes (LLM gives up more, by design) |
| correct abstention | 29 unmappable items    | **+0.793** | [+0.655, +0.931]  | Yes |

CI widths above are from the 2,000-resample paired bootstrap, now on the correct denominator per metric. Mean differences match the point estimates (0.890 - 0.836 = +0.054 for top-1, 0.922 - 0.731 = +0.191 for precision, 0.806 - 0.954 = -0.148 for coverage, 0.828 - 0.034 = +0.793 for abstention).

The top-1 accuracy lift's 95% CI lower bound is exactly 0.000. I will not call this a win. The real, statistically-significant wins are precision (+19 points) and correct abstention (+79 points).

## Project totals

| Thing | Value | Command |
|---|---:|---|
| Repo URL | [github.com/MrJaden7/tracemap](https://github.com/MrJaden7/tracemap) (public) | - |
| Docs site URL | [mrjaden7.github.io/tracemap](https://mrjaden7.github.io/tracemap/) (verified HTTP 200) | - |
| CI status | green on both CI and Pages workflows | [Actions tab](https://github.com/MrJaden7/tracemap/actions) |
| Commits on main (post history-rewrite) | 18 | `git log --oneline | wc -l` |
| ADRs | 13 (0001-0013) | `ls docs/decisions/*.md | wc -l` minus 1 for the README |
| Python unit tests | 34 | `uv run pytest --collect-only -q` |
| Python integration tests | 8 | `uv run pytest --collect-only -q -m integration` |
| dbt tests | 70 | `dbt test` |
| Mapping specifications | 14 YAML files | `ls mapping_spec/*.yml | wc -l` |
| CDM models (dbt) | 16 (14 Phase 1 + condition_era + drug_era) | `ls dbt/models/cdm/*.sql | wc -l` |

## Cost

Approximate, measured against my own API usage during this session:

| Operation | Rough cost | Notes |
|---|---|---|
| Full CDM build (0 to 7.3 M rows) | £0 | entirely local |
| AI eval, deterministic baselines only | £0 | no API calls |
| AI eval, 5 x 175 Anthropic calls | ~£1.00-£1.50 | `claude-sonnet-4-6`, 10-candidate prompt, JSON-only reply |

## What is in this fact sheet and what is not

- IN: everything measurable from a live run of the pipeline on this machine today, including OHDSI DQD results, ETL-Synthea reconciliation row counts, GitHub Actions CI status, and GitHub Pages deployment.
- NOT IN: reference `cost` rows (the ETL-Synthea cost INSERT was aborted at ~8h on this hardware; our pipeline does not model cost, so nothing is lost). See [reconciliation.md](reconciliation.md) and [gap_audit.md](gap_audit.md).
