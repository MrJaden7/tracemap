# `care_site`

**Spec version:** 0.1.0  
**Source systems:** synthea

One row per Synthea organization. The place_of_service_concept_id is left null in Phase 1 because Synthea's organization records have no service type field; in Phase 2 this will be inferred from the encounter classes seen at each organization.

## Source: `raw.synthea_organizations`

- **System:** synthea
- **Grain:** one row per organization

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `care_site_id` | `id` | lookup via `etl_meta.care_site_key_map` |  |
| `care_site_name` | `name` | copy |  |
| `place_of_service_concept_id` | `-` | constant = 0 (No matching concept) |  |
| `location_id` | `address` | lookup via `etl_meta.location_key_map` |  |
| `care_site_source_value` | `id` | copy |  |
| `place_of_service_source_value` | `-` | constant = None |  |

[Lineage diagram](../lineage/care_site.md)
