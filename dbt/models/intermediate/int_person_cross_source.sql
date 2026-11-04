-- The two source systems meet here via the HMAC linkage key. For every Synthea patient
-- we compute the same HMAC (that part is in the Python loader when the UK extract is
-- generated; the computed value is kept in etl_meta.synthea_linkage_keys, written as
-- part of the UK extract generation) and join the two maps on that.
--
-- In Phase 1 the Python generator didn't persist Synthea-side HMACs. Phase 2 writes a
-- small etl_meta.synthea_linkage_keys from the loader. We select it defensively here so
-- the model still works when no UK extract has been generated.

{{ config(materialized='view') }}

with uk as (
    select person_id as uk_person_id, source_patient_id as nhs_id, linkage_key
    from {{ ref('int_person_key_map_uk') }}
),
synthea as (
    select person_id as synthea_person_id, source_patient_id as synthea_id
    from {{ ref('int_person_key_map') }}
),
links as (
    select synthea_id, linkage_key from {{ source('etl_meta', 'synthea_linkage_keys') }}
)

select
    synthea.synthea_person_id,
    uk.uk_person_id,
    synthea.synthea_id,
    uk.nhs_id,
    uk.linkage_key
from synthea
join links on links.synthea_id   = synthea.synthea_id
join uk    on uk.linkage_key     = links.linkage_key
