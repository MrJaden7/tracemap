-- Staging view over raw.synthea_patients. One row per patient.
-- All source columns kept as text here; type casts happen in the CDM models so that each
-- cast is explicit alongside the mapping rule that chose it.

select
    _source_row,
    _run_id,
    id,
    birthdate,
    deathdate,
    first,
    last,
    marital,
    race,
    ethnicity,
    gender,
    birthplace,
    address,
    city,
    state,
    county,
    fips,
    zip
from {{ source('raw', 'synthea_patients') }}
