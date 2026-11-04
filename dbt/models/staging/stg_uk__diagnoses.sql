-- UK synthetic diagnoses. ICD-10 codes include deliberate messiness: whitespace, mixed
-- case, missing/extra dots, trailing zeros. normalise_icd10 cleans them up.

select
    _source_row,
    _run_id,
    nhs_id,
    admission_date,
    {{ normalise_icd10('icd10_code') }}  as icd10_code,
    icd10_code                            as icd10_source_value
from {{ source('raw', 'uk_diagnoses') }}
