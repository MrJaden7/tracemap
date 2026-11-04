select
    _source_row, _run_id, date, patient, encounter, category, code, description, value, units, type
from {{ source('raw', 'synthea_observations') }}
