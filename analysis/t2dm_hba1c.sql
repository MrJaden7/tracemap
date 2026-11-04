-- Cohort: patients with type 2 diabetes mellitus and at least two HbA1c measurements
-- in their observation period. Summary: patient count, latest HbA1c mean and median.
--
-- Concept selection:
--   Type 2 diabetes mellitus: SNOMED 44054006 (standard concept via Maps to)
--   HbA1c:                    LOINC 4548-4 (standard concept via Maps to)
--
-- Uses concept_ancestor so descendant conditions and HbA1c variants count too.

with t2dm_concepts as (
    select descendant_concept_id as concept_id
    from vocab.concept_ancestor a
    join vocab.concept c on c.concept_id = a.ancestor_concept_id
    where c.vocabulary_id = 'SNOMED' and c.concept_code = '44054006' and c.standard_concept = 'S'
),
hba1c_concepts as (
    select descendant_concept_id as concept_id
    from vocab.concept_ancestor a
    join vocab.concept c on c.concept_id = a.ancestor_concept_id
    where c.vocabulary_id = 'LOINC' and c.concept_code = '4548-4' and c.standard_concept = 'S'
),
t2dm_patients as (
    select distinct co.person_id
    from cdm.condition_occurrence co
    where co.condition_concept_id in (select concept_id from t2dm_concepts)
),
hba1c_values as (
    select m.person_id,
           m.measurement_date,
           m.value_as_number,
           row_number() over (partition by m.person_id order by m.measurement_date desc) as rn
    from cdm.measurement m
    where m.measurement_concept_id in (select concept_id from hba1c_concepts)
      and m.value_as_number is not null
),
hba1c_counts as (
    select person_id, count(*) as n_measurements
    from hba1c_values
    group by person_id
    having count(*) >= 2
),
cohort as (
    select p.person_id, lv.value_as_number as latest_hba1c
    from t2dm_patients p
    join hba1c_counts h   on h.person_id = p.person_id
    join hba1c_values lv  on lv.person_id = p.person_id and lv.rn = 1
)

select
    count(*)                        as n_patients,
    round(avg(latest_hba1c)::numeric, 2) as mean_latest_hba1c,
    round(percentile_cont(0.5) within group (order by latest_hba1c)::numeric, 2) as median_latest_hba1c
from cohort
