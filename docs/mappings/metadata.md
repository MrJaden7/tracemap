# `metadata`

**Spec version:** 0.1.0  
**Source systems:** tracemap

Free-form metadata about the CDM build. Populated at build time with the ETL version, Synthea version and seed, vocabulary version and the mapping spec version. All values are derived from etl_meta.cdm_run at build time; there is no source CSV.

## Source: `etl_meta.cdm_run`

- **System:** tracemap
- **Grain:** multiple rows per CDM build, one per metadata item

| Target field | Source column | Rule | Notes |
| --- | --- | --- | --- |
| `metadata_id` | `_derived_metadata_id` | castint |  |
| `metadata_concept_id` | `-` | constant = 0 (No matching concept) |  |
| `metadata_type_concept_id` | `-` | constant = 0 (No matching concept) |  |
| `name` | `_derived_name` | copy | etl_version, synthea_version, synthea_seed, vocabulary_version, spec_version. |
| `value_as_string` | `_derived_value` | copy |  |
| `metadata_date` | `_derived_metadata_date` | copy |  |

[Lineage diagram](../lineage/metadata.md)
