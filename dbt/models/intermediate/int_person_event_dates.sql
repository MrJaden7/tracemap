-- Min and max event dates per person across every clinical event table. Feeds
-- cdm.observation_period. Everything is already in raw, so we go straight to the
-- staging models.

{{ config(materialized='table', schema='intermediate', alias='person_event_dates') }}

with events as (
    select patient, start::date as event_date from {{ ref('stg_synthea__encounters') }}
    union all
    select patient, stop::date  from {{ ref('stg_synthea__encounters') }} where stop is not null and stop <> ''
    union all
    select patient, start::date from {{ ref('stg_synthea__conditions') }}
    union all
    select patient, date::date  from {{ ref('stg_synthea__observations') }}
    union all
    select patient, start::date from {{ ref('stg_synthea__medications') }}
    union all
    select patient, start::date from {{ ref('stg_synthea__procedures') }}
)

select
    patient                   as source_patient_id,
    min(event_date)           as min_event_date,
    max(event_date)           as max_event_date
from events
where event_date is not null
group by patient
