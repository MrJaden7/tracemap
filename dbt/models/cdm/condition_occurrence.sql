-- Overrides the generator's stub. Multi-source UNION of Synthea SNOMED conditions and
-- UK extract ICD-10 diagnoses. Condition occurrence id namespaces:
--   Synthea rows: raw._source_row (1 .. ~230k)
--   UK rows    : 100_000_000 + raw._source_row (so no collision is possible)
--
-- See mapping_spec/condition_occurrence.yml for the per-source rules this UNION implements.

{{ config(materialized='table', schema='cdm', alias='condition_occurrence') }}

with std_snomed as (
    select source_code, standard_concept_id
    from {{ ref('int_standard_concept_map') }}
    where source_vocabulary_id = 'SNOMED'
),
std_icd10 as (
    select source_code, standard_concept_id
    from {{ ref('int_standard_concept_map') }}
    where source_vocabulary_id = 'ICD10'
),
synthea_rows as (
    select
        c._source_row                                   as condition_occurrence_id,
        pk.person_id                                    as person_id,
        coalesce(std_snomed.standard_concept_id, 0)     as condition_concept_id,
        c.start::date                                   as condition_start_date,
        c.start::timestamp                              as condition_start_datetime,
        nullif(c.stop, '')::date                        as condition_end_date,
        nullif(c.stop, '')::timestamp                   as condition_end_datetime,
        32817                                           as condition_type_concept_id,
        c.code                                          as condition_source_value,
        coalesce(src.source_concept_id, 0)              as condition_source_concept_id,
        vm.visit_occurrence_id                          as visit_occurrence_id,
        'synthea'                                       as source_system
    from {{ ref('stg_synthea__conditions') }} c
    left join {{ ref('int_person_key_map') }}        pk on pk.source_patient_id = c.patient
    left join {{ ref('int_visit_source_key_map') }} vm on vm.source_id         = c.encounter
    left join std_snomed                                 on std_snomed.source_code = c.code
    left join {{ ref('int_source_concept_lookup') }} src on src.source_vocabulary_id = 'SNOMED'
                                                        and src.source_code         = c.code
),
uk_rows as (
    select
        100000000 + d._source_row                       as condition_occurrence_id,
        pm.person_id                                    as person_id,
        coalesce(std_icd10.standard_concept_id, 0)      as condition_concept_id,
        d.admission_date::date                          as condition_start_date,
        d.admission_date::timestamp                     as condition_start_datetime,
        null::date                                      as condition_end_date,
        null::timestamp                                 as condition_end_datetime,
        32817                                           as condition_type_concept_id,
        d.icd10_source_value                            as condition_source_value,
        coalesce(src.source_concept_id, 0)              as condition_source_concept_id,
        null::integer                                   as visit_occurrence_id,
        'uk_extract'                                    as source_system
    from {{ ref('stg_uk__diagnoses') }} d
    join {{ ref('int_person_key_map_uk') }} pm
        on pm.source_patient_id = d.nhs_id
    left join std_icd10                                 on std_icd10.source_code = d.icd10_code
    left join {{ ref('int_source_concept_lookup') }} src on src.source_vocabulary_id = 'ICD10'
                                                        and src.source_code         = d.icd10_code
)

select
    condition_occurrence_id,
    person_id,
    condition_concept_id,
    condition_start_date,
    condition_start_datetime,
    condition_end_date,
    condition_end_datetime,
    condition_type_concept_id,
    condition_source_value,
    condition_source_concept_id,
    visit_occurrence_id
from (
    select * from synthea_rows
    union all
    select * from uk_rows
) all_rows
