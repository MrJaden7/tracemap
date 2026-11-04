-- Synthea provider UUID -> integer provider_id.
{{ config(materialized='table', schema='etl_meta', alias='provider_key_map') }}

select
    row_number() over (order by _source_row) as provider_id,
    id as source_id,
    'synthea' as source_system,
    _run_id as run_id
from {{ ref('stg_synthea__providers') }}
