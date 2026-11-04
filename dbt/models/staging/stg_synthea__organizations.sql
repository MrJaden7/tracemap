select
    _source_row, _run_id, id, name, address, city, state, zip, lat, lon, phone
from {{ source('raw', 'synthea_organizations') }}
