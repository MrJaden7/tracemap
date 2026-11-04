# `procedure_occurrence`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea procedure record. Codes are SNOMED. Conditions and observations may also route here when the standard concept lands in the Procedure domain (domain routing, implemented in the intermediate layer).

## Source: `raw.synthea_procedures`

- **System:** synthea
- **Grain:** one row per procedure record

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `procedure_occurrence_id` | `_source_row` | castint |  |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `procedure_concept_id` | `code` | standard_concept_map (SNOMED, 'Maps to') (domain routing) |  |
| `procedure_date` | `start` | castdate |  |
| `procedure_datetime` | `start` | castdatetime |  |
| `procedure_end_date` | `stop` | castdate |  |
| `procedure_end_datetime` | `stop` | castdatetime |  |
| `procedure_type_concept_id` | `-` | constant = 32817 (EHR) |  |
| `procedure_source_value` | `code` | copy |  |
| `procedure_source_concept_id` | `code` | sourceconceptlookup |  |
| `visit_occurrence_id` | `encounter` | lookup via `etl_meta.visit_source_key_map` |  |

[Lineage diagram](../lineage/procedure_occurrence.md)
