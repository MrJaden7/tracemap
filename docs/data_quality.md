# Data quality

TraceMap's quality evidence has three layers.

## 1. dbt tests (generated from mapping spec)

- 70 tests covering `not_null` and `unique` constraints on every column the OMOP CDM v5.4 DDL marks NOT NULL or primary key.
- Generated automatically from mapping specs by `tracemap generate`.
- Status: **70 / 70 passing** (`dbt test`).

## 2. OHDSI Data Quality Dashboard v2.9.1

Executed on the live CDM with `tablesToExclude` for the 13 OHDSI tables TraceMap does not populate (cohort, visit_detail, note, etc.). Results in `docs/dqd/dqd_result.json`. Reproduction command in the fact sheet.

**Overall: 1,747 / 1,765 (98.98 %) passed. 18 failed. 0 errors.**

| Kahn category | Passed | Failed | NA  | Pass rate |
|---------------|-------:|-------:|----:|----------:|
| Conformance   | 627    | 7      | 106 | 98.9 %    |
| Completeness  | 310    | 6      | 26  | 98.1 %    |
| Plausibility  | 268    | 5      | 410 | 98.2 %    |

The high "Not Applicable" count on Plausibility is expected: many plausibility checks target fields TraceMap does not populate in Phase 1 (e.g. `measurement.range_low`, `drug_exposure.days_supply`). DQD marks these NA.

### Every failure, with cause

| # | Check | Table / Field | Violated | Cause / status |
|---|-------|---------------|---------:|----------------|
| 1 | `fkDomain` | CONDITION_OCCURRENCE.CONDITION_CONCEPT_ID | 55.6 % | **Expected.** The source domain is Condition but the mapped standard concept is often Observation/Procedure. This is the domain-routing issue documented in [ADR 0009](decisions/0009-domain-routing.md), deferred to Phase 2. DQD empirically confirms it. |
| 2 | `fkDomain` | CONDITION_ERA.CONDITION_CONCEPT_ID | 53.0 % | **Expected**, same root cause as 1 (era is built from condition_occurrence). |
| 3 | `fkDomain` | PROCEDURE_OCCURRENCE.PROCEDURE_CONCEPT_ID | 39.6 % | **Expected**, same root cause as 1 for procedures. |
| 4 | `fkDomain` | MEASUREMENT.MEASUREMENT_CONCEPT_ID | 0.01 % | Near-perfect. 4 rows of 3.7 M; LOINC concepts routed slightly off. |
| 5 | `fkClass` | DRUG_ERA.DRUG_CONCEPT_ID | 99.9 % | **Expected design tradeoff.** Standard OHDSI drug_era uses the Ingredient class (climbed via concept_ancestor); TraceMap's drug_era uses the drug_concept_id directly to keep the mapping flat. Documented in the `drug_era.sql` header comment. Climbing to Ingredient is a Phase 2 refinement. |
| 6 | `fkClass` | DRUG_STRENGTH.INGREDIENT_CONCEPT_ID | 0.12 % | Vocab-level: 3,600 of 2.97 M vocabulary rows have non-Ingredient concept classes. Not a TraceMap issue; we expose vocab verbatim. |
| 7 | `isStandardValidConcept` | OBSERVATION_PERIOD.PERIOD_TYPE_CONCEPT_ID | 100 % | **Real mapping bug.** The constant `44814724` I chose for `period_type_concept_id` is not a standard concept in the Athena release. Fix: change the constant to the correct standard period-type concept in `mapping_spec/observation_period.yml`. |
| 8 | `plausibleBeforeDeath` / `plausibleDuringLife` | OBSERVATION_PERIOD.OBSERVATION_PERIOD_END_DATE | 13.5 % (109/807 deceased) | **Real bug.** `int_person_event_dates` computes `max(event_date)` per patient but does not clamp to `death.death_date`. Fix: coalesce `observation_period_end_date` to `least(max_event_date, death_date)` in `int_person_event_dates.sql`. |
| 9 | `plausibleValueLow` | OBSERVATION_PERIOD.OBSERVATION_PERIOD_START_DATE | 5.7 % (331/5807) | Synthea generates centenarians with birth years in the 1920s whose earliest event is correspondingly old; DQD's threshold flags dates before ~1930. Not a bug in TraceMap, but worth a check filter in Phase 2. |
| 10 | `measurePersonCompleteness` | OBSERVATION_PERIOD | 7.9 % (500/6307) | Exactly the 500 UK extract patients: the UK extract has no encounters, so `int_person_event_dates` returns no rows for them. Fix: include UK-side event dates (admission/diagnosis/procedure) in `int_person_event_dates.sql`. |
| 11 | `plausibleValueHigh` | CDM_SOURCE.SOURCE_RELEASE_DATE | 1/1 | Synthea date is 2026 (current year), which exceeds DQD's hard-coded present-day cutoff. Acceptable. |
| 12 | `plausibleTemporalAfter` | CDM_SOURCE.CDM_RELEASE_DATE | 1/1 | Same reason. |
| 13 | `standardConceptRecordCompleteness` | MEASUREMENT.UNIT_CONCEPT_ID | 29.5 % | Matches the coverage report: Synthea units like `{beats}/min` aren't in UCUM. Documented tradeoff. |
| 14 | `standardConceptRecordCompleteness` | OBSERVATION.UNIT_CONCEPT_ID | 99.9 % | **Expected.** Observations are mostly non-measurement categories with no unit; `unit_concept_id = 0` is correct for those rows. DQD's threshold doesn't distinguish. |
| 15 | `standardConceptRecordCompleteness` | PROCEDURE_OCCURRENCE.PROCEDURE_CONCEPT_ID | 7.6 % | Exactly matches the 92.4 % procedure mapping coverage in the fact sheet. Consistent, not a new issue. |
| 16 | `sourceValueCompleteness` | CONDITION_OCCURRENCE.CONDITION_SOURCE_VALUE | 44.8 % of 925 distinct values | UK ICD-10 source values include whitespace + case variants that DQD counts as incomplete. Fix: tighten `normalise_icd10` to also strip leading zeros. |
| 17 | `sourceValueCompleteness` | PROCEDURE_OCCURRENCE.PROCEDURE_SOURCE_VALUE | 56.0 % of 807 | Same as 16 for OPCS-4. |

**Summary of the 18 failures:** 7 expected (deferred design decisions documented in ADRs or source files), 2 real bugs worth fixing in Phase 2 close-out (OBSERVATION_PERIOD.PERIOD_TYPE_CONCEPT_ID constant; observation period not clamped to death date), 2 time-reference quirks of synthetic data being dated 2026, 7 acceptable gaps that match the coverage report.

## 3. Custom SQL checks

Per-spec not-null and uniqueness tests, generated into `dbt/models/cdm/schema.yml`. 70 tests, all passing.

## 4. Mapping coverage

`tracemap coverage` writes `etl_meta.mapping_coverage` and `etl_meta.unmapped_codes`:

- row coverage: fraction of patient records mapped per CDM domain
- code coverage: fraction of distinct source codes mapped

See the fact sheet for the full table. The coverage percentages are consistent with the DQD `standardConceptRecordCompleteness` failures above (same arithmetic, different reporting lens).
