select
    _source_row, _run_id, start, stop, patient, encounter, code, description
from {{ source('raw', 'synthea_medications') }}
