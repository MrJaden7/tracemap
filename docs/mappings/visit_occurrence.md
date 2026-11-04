# `visit_occurrence`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea encounter. Encounter class strings (inpatient, outpatient, emergency and others) are mapped to Visit concepts in the intermediate layer via a reference table. The reasoning for each choice is recorded there and in ADR 0008.

## Source: `raw.synthea_encounters`

- **System:** synthea
- **Grain:** one row per encounter

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `visit_occurrence_id` | `_source_row` | castint | Deterministic surrogate key, source row number, so a rerun yields identical ids. |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `visit_concept_id` | `encounterclass` | lookup via `etl_meta.synthea_encounterclass_map` | inpatient->9201, outpatient->9202, emergency->9203, others documented in table. |
| `visit_start_date` | `start` | castdate |  |
| `visit_start_datetime` | `start` | castdatetime |  |
| `visit_end_date` | `stop` | castdate |  |
| `visit_end_datetime` | `stop` | castdatetime |  |
| `visit_type_concept_id` | `-` | constant = 32817 (EHR) | Synthea is generated as an EHR-style extract. |
| `care_site_id` | `organization` | lookup via `etl_meta.care_site_key_map` |  |
| `provider_id` | `provider` | lookup via `etl_meta.provider_key_map` |  |
| `visit_source_value` | `encounterclass` | copy |  |
| `visit_source_concept_id` | `-` | constant = 0 (No matching concept) |  |

[Lineage diagram](../lineage/visit_occurrence.md)
