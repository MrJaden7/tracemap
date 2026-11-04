-- Overrides the generator's stub. Mapping: mapping_spec/location.yml v0.1.0.
-- One row per distinct (address, city, state, zip) tuple from patients and organizations.

{{ config(materialized='table', schema='cdm', alias='location') }}

select
    location_id,
    address                           as address_1,
    null::text                        as address_2,
    city,
    state,
    zip,
    county,
    null::text                        as country,
    null::numeric                     as latitude,
    null::numeric                     as longitude,
    fips                              as location_source_value,
    null::integer                     as country_concept_id,
    null::text                        as country_source_value
from {{ ref('int_location') }}
