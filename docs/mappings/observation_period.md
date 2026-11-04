# `observation_period`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per patient covering the full span of observed events. Computed in the intermediate layer as MIN(event_date) to MAX(event_date) across every clinical event table (encounters, conditions, medications, observations, procedures, immunizations, allergies). The rule is intentionally simple: Synthea generates continuous records per patient, so a single period per person is correct.

## Source: `raw.synthea_patients`

- **System:** synthea
- **Grain:** one row per patient

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `observation_period_id` | `_source_row` | castint |  |
| `person_id` | `id` | lookup via `etl_meta.person_key_map` |  |
| `observation_period_start_date` | `__derived_min_event_date__` | copy | Computed in the intermediate layer, not from a source column. |
| `observation_period_end_date` | `__derived_max_event_date__` | copy | Computed in the intermediate layer, not from a source column. |
| `period_type_concept_id` | `-` | constant = 44814724 (Period covering healthcare encounters) | Verified against vocab.concept at build time. |

[Lineage diagram](../lineage/observation_period.md)
