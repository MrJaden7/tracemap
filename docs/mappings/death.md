# `death`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per deceased Synthea patient. Taken from patients.deathdate when non-null. Plausibility (no clinical events after death beyond a small tolerance) is a data quality test, not a mapping rule.

## Source: `raw.synthea_patients`

- **System:** synthea
- **Grain:** one row per deceased patient
- **Where:** `deathdate is not null and deathdate <> ''`

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `person_id` | `id` | lookup via `etl_meta.person_key_map` |  |
| `death_date` | `deathdate` | castdate |  |
| `death_datetime` | `deathdate` | castdatetime |  |
| `death_type_concept_id` | `-` | constant = 32817 (EHR) |  |

[Lineage diagram](../lineage/death.md)
