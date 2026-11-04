# Lineage: `observation_period`

```mermaid
flowchart LR
  src0["raw.synthea_patients"] --> stg0["staging"]
  km_etl_meta_person_key_map["etl_meta.person_key_map"] --> tgt["cdm.observation_period"]
  stg0 --> tgt["cdm.observation_period"]
```
