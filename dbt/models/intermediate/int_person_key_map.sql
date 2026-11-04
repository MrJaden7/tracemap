-- Maps Synthea patient UUIDs to an integer person_id. Deterministic: ordered by the row
-- number in the source file, so running the loader twice gives the same person_id for
-- the same patient. This is written to etl_meta so lineage can join to it later.

{{ config(materialized='table', schema='etl_meta', alias='person_key_map') }}

select
    row_number() over (order by _source_row) as person_id,
    id                                       as source_patient_id,
    'synthea'                                as source_system,
    _source_row                              as source_row,
    _run_id                                  as run_id
from {{ ref('stg_synthea__patients') }}
