select
    _source_row, _run_id, id, organization, name, gender, speciality, address, city, state, zip
from {{ source('raw', 'synthea_providers') }}
