-- Condition eras: contiguous periods of the same condition concept for one person.
-- Standard OHDSI logic: merge records whose gap is <= 30 days.
-- https://ohdsi.github.io/CommonDataModel/cdm54.html#condition_era

{{ config(materialized='table', schema='cdm', alias='condition_era') }}

with occ as (
    select person_id, condition_concept_id, condition_start_date, condition_end_date
    from {{ ref('condition_occurrence') }}
    where condition_concept_id <> 0
),
with_prev as (
    select
        person_id,
        condition_concept_id,
        condition_start_date,
        coalesce(condition_end_date, condition_start_date) as condition_end_date,
        lag(coalesce(condition_end_date, condition_start_date))
            over (partition by person_id, condition_concept_id order by condition_start_date) as prev_end
    from occ
),
flags as (
    select
        *,
        case
            when prev_end is null or condition_start_date - prev_end > 30 then 1
            else 0
        end as new_era_flag
    from with_prev
),
grouped as (
    select
        person_id,
        condition_concept_id,
        condition_start_date,
        condition_end_date,
        sum(new_era_flag) over (
            partition by person_id, condition_concept_id order by condition_start_date
        ) as era_id
    from flags
)

select
    row_number() over ()                                 as condition_era_id,
    person_id,
    condition_concept_id,
    min(condition_start_date)                            as condition_era_start_date,
    max(condition_end_date)                              as condition_era_end_date,
    count(*)                                             as condition_occurrence_count
from grouped
group by person_id, condition_concept_id, era_id
