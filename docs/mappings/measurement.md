# `measurement`

**Spec version:** 0.1.0  
**Source systems:** synthea

Synthea observations with category laboratory or vital-signs become measurements. Other observation categories route to the observation table. Codes are LOINC, units are mapped to UCUM. Numeric values populate value_as_number; non-numeric results are mapped to a value_as_concept_id where a mapping exists.

## Source: `raw.synthea_observations`

- **System:** synthea
- **Grain:** one row per observation, filtered in the intermediate layer to category IN ('laboratory', 'vital-signs')

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `measurement_id` | `_source_row` | castint |  |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `measurement_concept_id` | `code` | standard_concept_map (LOINC, 'Maps to') |  |
| `measurement_date` | `date` | castdate |  |
| `measurement_datetime` | `date` | castdatetime |  |
| `measurement_type_concept_id` | `-` | constant = 32817 (EHR) |  |
| `value_as_number` | `value` | castnumeric | Only when type = 'numeric'; non-numeric rows leave this null. |
| `value_as_concept_id` | `value` | valueasconceptmap | Only when type != 'numeric'. |
| `unit_concept_id` | `units` | unitmap |  |
| `unit_source_value` | `units` | copy |  |
| `measurement_source_value` | `code` | copy |  |
| `measurement_source_concept_id` | `code` | sourceconceptlookup |  |
| `value_source_value` | `value` | copy |  |
| `visit_occurrence_id` | `encounter` | lookup via `etl_meta.visit_source_key_map` |  |

[Lineage diagram](../lineage/measurement.md)
