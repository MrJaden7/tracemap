select
    _source_row, _run_id, start, stop, patient, encounter, "system" as code_system, code, description
from {{ source('raw', 'synthea_procedures') }}
