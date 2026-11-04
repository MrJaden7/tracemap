-- Drug eras: contiguous periods of the same ingredient. Simpler than condition eras in
-- Phase 2 because we do not yet climb to the ingredient level via concept_ancestor; the
-- drug_concept_id itself is used as the grouping key. ADR will capture the tradeoff.

{{ config(materialized='table', schema='cdm', alias='drug_era') }}

with exp as (
    select person_id, drug_concept_id, drug_exposure_start_date, drug_exposure_end_date
    from {{ ref('drug_exposure') }}
    where drug_concept_id <> 0
),
with_prev as (
    select
        person_id,
        drug_concept_id,
        drug_exposure_start_date as start_date,
        coalesce(drug_exposure_end_date, drug_exposure_start_date) as end_date,
        lag(coalesce(drug_exposure_end_date, drug_exposure_start_date))
            over (partition by person_id, drug_concept_id order by drug_exposure_start_date) as prev_end
    from exp
),
flags as (
    select *,
        case when prev_end is null or start_date - prev_end > 30 then 1 else 0 end as new_era_flag
    from with_prev
),
grouped as (
    select person_id, drug_concept_id, start_date, end_date,
           sum(new_era_flag) over (
               partition by person_id, drug_concept_id order by start_date
           ) as era_id
    from flags
)

select
    row_number() over ()                 as drug_era_id,
    person_id,
    drug_concept_id,
    min(start_date)                      as drug_era_start_date,
    max(end_date)                        as drug_era_end_date,
    count(*)                             as drug_exposure_count,
    null::integer                        as gap_days
from grouped
group by person_id, drug_concept_id, era_id
