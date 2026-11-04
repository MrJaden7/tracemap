-- UK synthetic patients. linkage_key is HMAC-SHA256(synthea_id, salt): the only way to
-- link UK records back to Synthea records is to compute the same HMAC on the Synthea
-- side, which lives in etl_meta.person_key_map's linkage column (built by
-- int_person_key_map_uk).

select
    _source_row,
    _run_id,
    nhs_id,
    linkage_key,
    birthdate,
    gender,
    postcode_district
from {{ source('raw', 'uk_patients') }}
