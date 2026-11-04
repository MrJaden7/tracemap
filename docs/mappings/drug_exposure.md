# `drug_exposure`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea medication record. Synthea codes drugs in RxNorm, which OMOP treats as a standard vocabulary, so the standard concept mapping is effectively a pass-through that only fills in the correct concept_id.

## Source: `raw.synthea_medications`

- **System:** synthea
- **Grain:** one row per medication record

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `drug_exposure_id` | `_source_row` | castint |  |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `drug_concept_id` | `code` | standard_concept_map (RxNorm, 'Maps to') |  |
| `drug_exposure_start_date` | `start` | castdate |  |
| `drug_exposure_start_datetime` | `start` | castdatetime |  |
| `drug_exposure_end_date` | `stop` | castdate |  |
| `drug_exposure_end_datetime` | `stop` | castdatetime |  |
| `verbatim_end_date` | `stop` | castdate |  |
| `drug_type_concept_id` | `-` | constant = 32817 (EHR) | Synthea medications come from an EHR-style export. |
| `drug_source_value` | `code` | copy |  |
| `drug_source_concept_id` | `code` | sourceconceptlookup |  |
| `visit_occurrence_id` | `encounter` | lookup via `etl_meta.visit_source_key_map` |  |

[Lineage diagram](../lineage/drug_exposure.md)
