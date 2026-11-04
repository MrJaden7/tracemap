# `provider`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea provider. Speciality is a free text in Synthea; a mapping to Provider speciality concepts is out of scope for Phase 1.

## Source: `raw.synthea_providers`

- **System:** synthea
- **Grain:** one row per provider

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `provider_id` | `id` | lookup via `etl_meta.provider_key_map` |  |
| `provider_name` | `name` | copy |  |
| `gender_concept_id` | `gender` | standard_concept_map (Gender, 'Maps to') |  |
| `specialty_concept_id` | `-` | constant = 0 (No matching concept) | Synthea speciality strings are not mapped in Phase 1. |
| `care_site_id` | `organization` | lookup via `etl_meta.care_site_key_map` |  |
| `provider_source_value` | `id` | copy |  |
| `specialty_source_value` | `speciality` | copy |  |
| `gender_source_value` | `gender` | copy |  |

[Lineage diagram](../lineage/provider.md)
