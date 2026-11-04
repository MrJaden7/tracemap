# Lineage: `drug_exposure`

```mermaid
flowchart LR
  src0["raw.synthea_medications"] --> stg0["staging"]
  km_etl_meta_person_key_map["etl_meta.person_key_map"] --> tgt["cdm.drug_exposure"]
  km_etl_meta_visit_source_key_map["etl_meta.visit_source_key_map"] --> tgt["cdm.drug_exposure"]
  std_rxnorm["vocab.RxNorm → standard"] --> tgt["cdm.drug_exposure"]
  stg0 --> tgt["cdm.drug_exposure"]
```
