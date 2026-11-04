-- UK patients -> integer person_id. Linkage to Synthea patients is by linkage_key =
-- HMAC-SHA256(synthea_id, salt), computed by the Python loader; this model preserves it
-- so downstream analysis can see which patient appears in both sources.
--
-- UK person_ids start at 10_000_000 to avoid clashing with Synthea person_ids.

{{ config(materialized='table', schema='etl_meta', alias='person_key_map_uk') }}

select
    10000000 + row_number() over (order by _source_row) as person_id,
    nhs_id                                              as source_patient_id,
    'uk_extract'                                        as source_system,
    linkage_key                                         as linkage_key,
    _source_row                                         as source_row,
    _run_id                                             as run_id
from {{ ref('stg_uk__patients') }}
