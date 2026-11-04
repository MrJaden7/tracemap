-- Overrides the generator's stub. Mapping: mapping_spec/observation.yml v0.1.0.
-- Target: cdm.observation
-- Source: raw.synthea_observations filtered to category NOT IN ('laboratory', 'vital-signs').

{{ config(materialized='table', schema='cdm', alias='observation') }}

with obs as (
    select *
    from {{ ref('stg_synthea__observations') }}
    where category not in ('laboratory', 'vital-signs')
),
std as (
    select source_code, standard_concept_id
    from {{ ref('int_standard_concept_map') }}
    where source_vocabulary_id = 'LOINC'
)

select
    obs._source_row                                       as observation_id,
    km.person_id                                          as person_id,
    coalesce(std.standard_concept_id, 0)                  as observation_concept_id,
    obs.date::date                                        as observation_date,
    obs.date::timestamp                                   as observation_datetime,
    32817                                                 as observation_type_concept_id,
    case when obs.type = 'numeric' and obs.value ~ '^-?\d+(\.\d+)?$'
         then obs.value::numeric end                      as value_as_number,
    case when obs.type != 'numeric' then obs.value end    as value_as_string,
    null::integer                                         as value_as_concept_id,
    null::integer                                         as qualifier_concept_id,
    coalesce(unit.concept_id, 0)                          as unit_concept_id,
    null::integer                                         as provider_id,
    vm.visit_occurrence_id                                as visit_occurrence_id,
    null::integer                                         as visit_detail_id,
    obs.code                                              as observation_source_value,
    src.source_concept_id                                 as observation_source_concept_id,
    obs.units                                             as unit_source_value,
    null::text                                            as qualifier_source_value,
    null::integer                                         as value_source_concept_id,
    obs.value                                             as value_source_value,
    null::integer                                         as observation_event_id,
    null::integer                                         as obs_event_field_concept_id
from obs
left join {{ ref('int_person_key_map') }}        km on km.source_patient_id = obs.patient
left join {{ ref('int_visit_source_key_map') }} vm on vm.source_id         = obs.encounter
left join std                                      on std.source_code      = obs.code
left join {{ ref('int_source_concept_lookup') }} src on src.source_vocabulary_id = 'LOINC'
                                                     and src.source_code   = obs.code
left join {{ ref('int_ucum_unit_map') }}       unit on unit.source_unit    = obs.units
