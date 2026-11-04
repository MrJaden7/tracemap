-- UK synthetic procedures. Same normalisation story as diagnoses.

select
    _source_row,
    _run_id,
    nhs_id,
    procedure_date,
    {{ normalise_opcs4('opcs4_code') }}   as opcs4_code,
    opcs4_code                            as opcs4_source_value
from {{ source('raw', 'uk_procedures') }}
