# ADR 0003: Vocabulary selection and release

- Status: Accepted
- Date: 2026-11-04

## Context

OMOP mapping depends on the OMOP Standardized Vocabularies, downloaded from Athena (athena.ohdsi.org). They are licensed for download and must not be redistributed, so they are never committed (`data/` is gitignored). The project brief listed the vocabularies to select.

## Decision

Release **v5.0 29-AUG-26** (Athena bundle v20260829), downloaded 4 November 2026.

Selected for TraceMap's mappings:

| Vocabulary | Why |
|---|---|
| SNOMED | Synthea conditions and procedures. The bundle includes the SNOMED CT UK Edition (2026-04-08) as well as the International and US editions. |
| ICD10 (WHO) | UK hospital diagnoses (Phase 2). The WHO version is used in the UK, not the US ICD10CM. |
| OPCS4 | UK hospital procedures (Phase 2). |
| dm+d | UK medicines. Documented as the UK equivalent of RxNorm. |
| RxNorm, RxNorm Extension | Synthea medications. |
| LOINC | Synthea observations and lab results. |
| UCUM | Measurement units. |
| **CVX** | **Added beyond the original brief.** Synthea codes immunisations in CVX. Without it every immunisation would map to concept 0. |
| Gender, Race, Ethnicity, Visit, Type Concept, Domain, Vocabulary, Concept Class, Relationship | OMOP reference vocabularies. Athena includes these in every bundle automatically and does not list them for selection. Their presence was confirmed in `VOCABULARY.csv`. |

Excluded: **CPT4**. It needs a separate UMLS licence and a post-download step to fill in concept names, and Synthea does not use it.

Other default Athena vocabularies (ICD9CM, ICD10CM, HCPCS, NDC, ATC, NUCC and others) were left in the bundle. They are unused but harmless.

## Verification

`tracemap vocab check` confirms every required vocabulary is present before anything is loaded. A missing vocabulary stops the load and is named in the error.

## Consequences

- The release string is recorded in `etl_meta.vocabulary_load` and will be written to `CDM_SOURCE.vocabulary_version`.
- Anyone reproducing the results needs their own free Athena account and the same selection.

## In plain English

The coding systems needed for both the US-style synthetic data and the UK-style hospital extract were downloaded, including one (CVX, for vaccines) that the original plan missed. The pipeline checks they are all present before it starts.
