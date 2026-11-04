# Lineage: `condition_occurrence`

```mermaid
flowchart LR
  src0["raw.synthea_conditions"] --> stg0["staging"]
  km_etl_meta_person_key_map["etl_meta.person_key_map"] --> tgt["cdm.condition_occurrence"]
  km_etl_meta_visit_source_key_map["etl_meta.visit_source_key_map"] --> tgt["cdm.condition_occurrence"]
  std_snomed["vocab.SNOMED → standard"] --> tgt["cdm.condition_occurrence"]
  stg0 --> tgt["cdm.condition_occurrence"]
```
