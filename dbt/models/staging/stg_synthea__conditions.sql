-- Staging view over raw.synthea_conditions.

select
    _source_row,
    _run_id,
    patient,
    encounter,
    start,
    stop,
    "system" as code_system,
    code,
    description
from {{ source('raw', 'synthea_conditions') }}
