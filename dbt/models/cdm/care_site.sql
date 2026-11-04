-- Overrides the generator's stub. Mapping: mapping_spec/care_site.yml v0.1.0.
-- One row per Synthea organization, joined to its deduplicated location via address.

{{ config(materialized='table', schema='cdm', alias='care_site') }}

select
    km.care_site_id,
    org.name                          as care_site_name,
    0                                 as place_of_service_concept_id,
    loc.location_id                   as location_id,
    org.id                            as care_site_source_value,
    null::text                        as place_of_service_source_value
from {{ ref('stg_synthea__organizations') }} org
join {{ ref('int_care_site_key_map') }} km
    on km.source_id = org.id
left join {{ ref('int_location') }} loc
    on trim(loc.address) = trim(org.address)
   and trim(loc.city)    = trim(org.city)
   and trim(loc.state)   = trim(org.state)
   and trim(loc.zip)     = trim(org.zip)
