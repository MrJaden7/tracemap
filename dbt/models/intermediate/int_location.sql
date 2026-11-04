-- Deduplicated locations across patients and organizations. Writes to etl_meta so
-- cdm.location and cdm.care_site/cdm.person can join back.

{{ config(materialized='table', schema='etl_meta', alias='location_key_map') }}

with addresses as (
    select trim(address) as address, trim(city) as city, trim(state) as state,
           trim(zip) as zip, trim(county) as county, trim(fips) as fips
    from {{ ref('stg_synthea__patients') }}
    union
    select trim(address) as address, trim(city) as city, trim(state) as state,
           trim(zip) as zip, null as county, null as fips
    from {{ ref('stg_synthea__organizations') }}
)

select
    row_number() over (order by address, city, state, zip) as location_id,
    address, city, state, zip, county, fips
from addresses
