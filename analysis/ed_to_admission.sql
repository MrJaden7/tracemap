-- Care pathway: emergency visits followed by an inpatient admission within 7 days.
-- Uses visit_concept_id to identify visit types.
--   Emergency Room Visit: 9203
--   Inpatient Visit     : 9201

with emergency as (
    select person_id, visit_occurrence_id, visit_start_date
    from cdm.visit_occurrence
    where visit_concept_id = 9203
),
inpatient as (
    select person_id, visit_occurrence_id, visit_start_date
    from cdm.visit_occurrence
    where visit_concept_id = 9201
),
linked as (
    select
        e.person_id,
        e.visit_start_date as emergency_date,
        i.visit_start_date as inpatient_date,
        i.visit_start_date - e.visit_start_date as days_to_admission
    from emergency e
    join inpatient i
      on i.person_id = e.person_id
     and i.visit_start_date between e.visit_start_date and e.visit_start_date + interval '7 day'
)

select
    date_trunc('year', emergency_date)::date as year,
    count(distinct person_id)                 as n_patients,
    count(*)                                  as n_pathways,
    round(avg(days_to_admission)::numeric, 2) as mean_days_to_admission
from linked
group by 1
order by 1 desc
