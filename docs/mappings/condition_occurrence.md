# `condition_occurrence`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea condition record. Codes are SNOMED. Mapping a SNOMED code to its standard concept via `Maps to` may land the row in the Procedure or Observation domain; when it does, domain routing in the intermediate layer moves the row to procedure_occurrence or observation rather than forcing it here.

## Source: `raw.synthea_conditions`

- **System:** synthea
- **Grain:** one row per condition record

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `condition_occurrence_id` | `_source_row` | castint |  |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `condition_concept_id` | `code` | standard_concept_map (SNOMED, 'Maps to') (domain routing) |  |
| `condition_start_date` | `start` | castdate |  |
| `condition_start_datetime` | `start` | castdatetime |  |
| `condition_end_date` | `stop` | castdate |  |
| `condition_end_datetime` | `stop` | castdatetime |  |
| `condition_type_concept_id` | `-` | constant = 32817 (EHR) | Synthea is an EHR-style export. |
| `condition_source_value` | `code` | copy |  |
| `condition_source_concept_id` | `code` | sourceconceptlookup |  |
| `visit_occurrence_id` | `encounter` | lookup via `etl_meta.visit_source_key_map` |  |

[Lineage diagram](../lineage/condition_occurrence.md)
