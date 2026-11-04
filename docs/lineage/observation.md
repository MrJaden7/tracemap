# Lineage: `observation`

```mermaid
flowchart LR
  src0["raw.synthea_observations"] --> stg0["staging"]
  km_etl_meta_person_key_map["etl_meta.person_key_map"] --> tgt["cdm.observation"]
  km_etl_meta_visit_source_key_map["etl_meta.visit_source_key_map"] --> tgt["cdm.observation"]
  std_loinc["vocab.LOINC → standard"] --> tgt["cdm.observation"]
  stg0 --> tgt["cdm.observation"]
```
