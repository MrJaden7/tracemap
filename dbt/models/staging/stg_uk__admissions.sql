select
    _source_row, _run_id, nhs_id, spell_id, admission_date, discharge_date, admission_type
from {{ source('raw', 'uk_admissions') }}
