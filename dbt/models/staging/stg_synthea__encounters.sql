-- Staging view over raw.synthea_encounters.

select
    _source_row,
    _run_id,
    id,
    start,
    stop,
    patient,
    organization,
    provider,
    payer,
    encounterclass,
    code,
    description,
    reasoncode,
    reasondescription
from {{ source('raw', 'synthea_encounters') }}
