-- Overrides the generator's stub. Multi-source UNION of Synthea patients and UK patients.
-- Synthea person_ids start at 1, UK person_ids start at 10_000_000 (see int_person_key_map_uk).

{{ config(materialized='table', schema='cdm', alias='person') }}

with synthea_rows as (
    select
        pk.person_id,
        coalesce(g.gender_concept_id, 0)                   as gender_concept_id,
        cast(extract(year  from p.birthdate::date) as int) as year_of_birth,
        cast(extract(month from p.birthdate::date) as int) as month_of_birth,
        cast(extract(day   from p.birthdate::date) as int) as day_of_birth,
        p.birthdate::timestamp                             as birth_datetime,
        0                                                  as race_concept_id,
        0                                                  as ethnicity_concept_id,
        p.id                                               as person_source_value,
        p.gender                                           as gender_source_value,
        p.race                                             as race_source_value,
        p.ethnicity                                        as ethnicity_source_value
    from {{ ref('stg_synthea__patients') }} p
    join {{ ref('int_person_key_map') }} pk on pk.source_patient_id = p.id
    left join {{ ref('int_gender_lookup') }} g on g.source_code  = p.gender
),
uk_rows as (
    select
        pm.person_id,
        case upper(u.gender)
            when 'M' then 8507
            when 'F' then 8532
            else 0 end                                     as gender_concept_id,
        cast(extract(year  from u.birthdate::date) as int) as year_of_birth,
        cast(extract(month from u.birthdate::date) as int) as month_of_birth,
        cast(extract(day   from u.birthdate::date) as int) as day_of_birth,
        u.birthdate::timestamp                             as birth_datetime,
        0                                                  as race_concept_id,
        0                                                  as ethnicity_concept_id,
        u.nhs_id                                           as person_source_value,
        u.gender                                           as gender_source_value,
        null::text                                         as race_source_value,
        null::text                                         as ethnicity_source_value
    from {{ ref('stg_uk__patients') }} u
    join {{ ref('int_person_key_map_uk') }} pm on pm.source_patient_id = u.nhs_id
)

select
    person_id,
    gender_concept_id,
    year_of_birth, month_of_birth, day_of_birth, birth_datetime,
    race_concept_id, ethnicity_concept_id,
    null::integer                        as location_id,
    null::integer                        as provider_id,
    null::integer                        as care_site_id,
    person_source_value,
    gender_source_value,
    null::integer                        as gender_source_concept_id,
    race_source_value,
    null::integer                        as race_source_concept_id,
    ethnicity_source_value,
    null::integer                        as ethnicity_source_concept_id
from (
    select * from synthea_rows
    union all
    select * from uk_rows
) all_persons
