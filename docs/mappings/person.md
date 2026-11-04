# `person`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per distinct source patient. Synthea patients are keyed by UUID, which is mapped to the integer person_id via etl_meta.person_key_map. Race and ethnicity are stored as source_value only in Phase 1 (Synthea categories are US-specific and do not match UK ethnicity coding; a mapping table is out of scope).

## Source: `raw.synthea_patients`

- **System:** synthea
- **Grain:** one row per patient

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `person_id` | `id` | lookup via `etl_meta.person_key_map` | Synthea UUID mapped to integer person_id. |
| `gender_concept_id` | `gender` | standard_concept_map (Gender, 'Maps to') | Synthea values M and F map to Gender concepts 8507 and 8532. |
| `year_of_birth` | `birthdate` | castint | Year extracted from birthdate (YYYY-MM-DD). |
| `month_of_birth` | `birthdate` | castint |  |
| `day_of_birth` | `birthdate` | castint |  |
| `birth_datetime` | `birthdate` | castdatetime |  |
| `race_concept_id` | `-` | constant = 0 (No matching concept) | Synthea race categories are US-specific; left unmapped in Phase 1. |
| `ethnicity_concept_id` | `-` | constant = 0 (No matching concept) | Synthea ethnicity values are US-specific. |
| `person_source_value` | `id` | copy |  |
| `gender_source_value` | `gender` | copy |  |
| `race_source_value` | `race` | copy |  |
| `ethnicity_source_value` | `ethnicity` | copy |  |

[Lineage diagram](../lineage/person.md)
