-- Ongoing medications in Synthea leave stop null. OMOP CDM requires
-- drug_exposure_end_date, and the standard convention is to carry start forward so the
-- exposure has a defined end (usually of equal length to start if unknown). Documented
-- here where the transform happens.
select
    _source_row,
    _run_id,
    start,
    nullif(stop, '')                                        as stop_raw,
    case when nullif(stop, '') is null then start else stop end as stop,
    patient,
    encounter,
    code,
    description
from {{ source('raw', 'synthea_medications') }}
