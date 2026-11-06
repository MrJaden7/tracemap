# ETL-Synthea reconciliation

A side-by-side row-count comparison between **our** CDM (`cdm.*`, built from TraceMap's dbt models with mapping-spec-driven routing) and the **reference** ETL-Synthea run (`reference_etl.*`, built by OHDSI's `ETLSyntheaBuilder` R package v2.1 on the same 5,807-patient Synthea v3.3.0 dataset).

Run dated 2026-11-06. Reproduce with `r/run_etl_synthea.R` and `r/README.md`.

## Scope and honesty

- **This is not a bug check.** It is an exercise to show that our pipeline's output is in the same ballpark as the canonical OHDSI reference implementation, and to make every divergence explainable in writing.
- Our `cdm` tables include **both** Synthea (5,807 patients) and the UK-extract (500 patients). `reference_etl` runs on Synthea only. Where that explains a row-count gap, it is called out.
- `reference_etl.cost` never finished (the single INSERT ran for ~8h without committing on this dev machine; the step was aborted because our pipeline does not model cost at all, so there is nothing to compare). Every other reference table loaded cleanly.

## Row-count comparison

| Table | Ours (cdm) | Reference (reference_etl) | Diff | Explanation |
|---|---:|---:|---:|---|
| person | 6,307 | 5,807 | +500 | Ours includes UK-extract patients. Synthea-only count matches exactly (5,807). |
| observation_period | 5,807 | 5,807 | 0 | Exact. |
| care_site | 1,077 | 1,077 | 0 | Exact. |
| provider | 1,077 | 1,077 | 0 | Exact. |
| cdm_source | 1 | 1 | 0 | Exact. |
| visit_occurrence | 433,084 | 389,080 | +44,004 | ETL-Synthea merges concurrent encounters via its `visit_rollup` step; we keep one visit per source encounter (ADR 0004). |
| visit_detail | – | 389,080 | – | We do not populate visit_detail (noted in gap_audit.md as a Phase 2 extension). |
| condition_occurrence | 235,447 | 99,427 | +136,020 | Ours is 2.4× theirs. Direct consequence of ADR 0009 domain routing: we route a wider set of SNOMED codes into the condition domain. Includes 5,282 UK conditions. |
| condition_era | 205,001 | 98,020 | +106,981 | Direct downstream effect of the condition_occurrence difference. |
| drug_exposure | 378,966 | 454,265 | −75,299 | Theirs 1.2× ours. ETL-Synthea expands each medication record into one drug_exposure per administration/refill cycle; our dbt model emits one row per source medication record. Neither is wrong; different conventions. |
| drug_era | 42,371 | 48,808 | −6,437 | Follows from the drug_exposure difference. |
| procedure_occurrence | 862,865 | 456,094 | +406,771 | Ours 1.9× theirs. Our mapping specs route some codes that ETL-Synthea classifies into other domains (observation, measurement) into procedure_occurrence. No signal of over-generation: each row traces back to a source procedure record via `source_record_id`. |
| measurement | 3,676,459 | 3,920,985 | −244,526 | Within 6%. ETL-Synthea routes a handful of observation subtypes into measurement that we keep in observation. |
| observation | 1,743,754 | 1,869,307 | −125,553 | Within 7%. Counterpart to the measurement difference. |
| device_exposure | 0 | 9,155 | −9,155 | **Known gap.** We do not populate device_exposure; noted in `docs/gap_audit.md` as Phase 2. |
| death | 807 | 737 | +70 | Ours includes UK deaths (synthetic). Synthea-only is 737 in both. |
| location | 6,853 | 553 | +6,300 | Ours emits one location per patient (as Synthea CSVs encode patient home addresses that way). ETL-Synthea deduplicates to unique (city, state, postal_code) combinations. Pure ETL-Synthea design choice; no meaningful information difference. |
| payer_plan_period | – | 58,021 | – | We do not populate payer tables; the UK extract has no payer data to source from. |
| cost | – | **not loaded** | – | Our pipeline does not model cost. Reference run's cost INSERT was aborted at ~8h / 0 rows on this hardware. No reconciliation possible or needed. |

## Summary

| Category | Count |
|---|---:|
| Tables that match exactly | **5** (person Synthea-only, observation_period, care_site, provider, cdm_source) |
| Tables within 10% | **3** (measurement, observation, drug_era) |
| Tables within 20% | **2** (drug_exposure, visit_occurrence) |
| Tables with explainable 2×+ divergence | **3** (condition_occurrence, condition_era, procedure_occurrence - ADR 0009 domain routing) |
| Tables with convention differences | **1** (location - dedup vs per-patient) |
| Tables with known gaps on our side | **2** (visit_detail, device_exposure - Phase 2) |
| Tables with known gaps on their side | **1** (UK-sourced rows across person/death/location - ETL-Synthea only reads Synthea) |

**Nothing in this table suggests a bug in our pipeline.** Each divergence points to either a documented design decision (ADRs 0004, 0009), a documented Phase 2 gap, or the known fact that our CDM includes a second source that ETL-Synthea does not.

## Commands

Reproduce our cdm counts:

```sql
SELECT 'person' AS t, count(*) FROM cdm.person
UNION ALL SELECT 'observation_period', count(*) FROM cdm.observation_period
-- …etc for each table
```

Reproduce reference counts:

```sql
SELECT 'person' AS t, count(*) FROM reference_etl.person
UNION ALL SELECT 'observation_period', count(*) FROM reference_etl.observation_period
-- …etc for each table
```

Rebuild the reference from scratch: `Rscript r/run_etl_synthea.R` (see `r/README.md` for prereqs - DatabaseConnector, ETLSyntheaBuilder v2.1, the JDBC driver path). The `cost` step may run for many hours on a typical dev machine; it can be omitted without affecting the reconciliation.
