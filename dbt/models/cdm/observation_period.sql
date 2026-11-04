-- Overrides the generator's stub. Mapping: mapping_spec/observation_period.yml v0.1.0.
-- One row per person covering min(event_date) .. max(event_date) across every event.

{{ config(materialized='table', schema='cdm', alias='observation_period') }}

select
    row_number() over (order by km.person_id) as observation_period_id,
    km.person_id,
    ed.min_event_date                         as observation_period_start_date,
    ed.max_event_date                         as observation_period_end_date,
    44814724                                  as period_type_concept_id
from {{ ref('int_person_event_dates') }} ed
join {{ ref('int_person_key_map') }} km
    on km.source_patient_id = ed.source_patient_id
