-- Synthea encounter class strings -> Visit concept_ids. Chosen per OMOP conventions:
--   inpatient / snf / hospice -> 9201 (Inpatient Visit)
--   outpatient / ambulatory / wellness / home / virtual -> 9202 (Outpatient Visit)
--   emergency / urgentcare -> 9203 (Emergency Room Visit)
-- Each choice is reviewed as the UK extract is added in Phase 2.

{{ config(materialized='table', schema='etl_meta', alias='synthea_encounterclass_map') }}

with mapping (source_id, visit_concept_id, note) as (
    values
        ('inpatient',   9201, 'OMOP Inpatient Visit'),
        ('snf',         9201, 'Skilled nursing facility; nearest match'),
        ('hospice',     9201, 'Hospice care; nearest match'),
        ('outpatient',  9202, 'OMOP Outpatient Visit'),
        ('ambulatory',  9202, 'Ambulatory outpatient visit'),
        ('wellness',    9202, 'Wellness/check-up; outpatient'),
        ('home',        9202, 'Home visit; outpatient'),
        ('virtual',     9202, 'Telehealth; outpatient'),
        ('emergency',   9203, 'Emergency Room Visit'),
        ('urgentcare',  9203, 'Urgent care; mapped to ER as closest analogue')
)
select
    source_id,
    visit_concept_id,
    note
from mapping
