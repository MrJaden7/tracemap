-- Maps Synthea encounter UUIDs to the integer visit_occurrence_id used in the CDM.

{{ config(materialized='table', schema='etl_meta', alias='visit_source_key_map') }}

select
    _source_row as visit_occurrence_id,
    id          as source_id,
    'synthea'   as source_system,
    _run_id     as run_id
from {{ ref('stg_synthea__encounters') }}
