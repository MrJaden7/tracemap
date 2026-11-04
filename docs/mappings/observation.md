# `observation`

**Spec version:** 0.1.0  
**Source systems:** synthea

Synthea observations that are not laboratory or vital-signs become OMOP observations (survey, social-history, exam, therapy, procedure, imaging). Also receives Synthea conditions and procedures whose SNOMED standard concept is in the Observation domain via domain routing.

## Source: `raw.synthea_observations`

- **System:** synthea
- **Grain:** one row per observation, filtered in the intermediate layer to category NOT IN ('laboratory', 'vital-signs')

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `observation_id` | `_source_row` | castint |  |
| `person_id` | `patient` | lookup via `etl_meta.person_key_map` |  |
| `observation_concept_id` | `code` | standard_concept_map (LOINC, 'Maps to') |  |
| `observation_date` | `date` | castdate |  |
| `observation_datetime` | `date` | castdatetime |  |
| `observation_type_concept_id` | `-` | constant = 32817 (EHR) |  |
| `value_as_number` | `value` | castnumeric |  |
| `value_as_string` | `value` | copy |  |
| `value_as_concept_id` | `value` | valueasconceptmap |  |
| `unit_concept_id` | `units` | unitmap |  |
| `unit_source_value` | `units` | copy |  |
| `observation_source_value` | `code` | copy |  |
| `observation_source_concept_id` | `code` | sourceconceptlookup |  |
| `visit_occurrence_id` | `encounter` | lookup via `etl_meta.visit_source_key_map` |  |

[Lineage diagram](../lineage/observation.md)
