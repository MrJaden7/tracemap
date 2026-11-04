-- Cohort: new hypertension diagnoses per calendar year by sex and age band.
-- A "new" diagnosis means the person's first hypertension condition record.
--
-- Concept selection: essential hypertension SNOMED 59621000 and descendants.

with htn_concepts as (
    select descendant_concept_id as concept_id
    from vocab.concept_ancestor a
    join vocab.concept c on c.concept_id = a.ancestor_concept_id
    where c.vocabulary_id = 'SNOMED' and c.concept_code = '59621000' and c.standard_concept = 'S'
),
first_htn as (
    select person_id, min(condition_start_date) as first_diagnosis_date
    from cdm.condition_occurrence
    where condition_concept_id in (select concept_id from htn_concepts)
    group by person_id
),
labelled as (
    select
        f.person_id,
        extract(year from f.first_diagnosis_date)::int as diagnosis_year,
        case p.gender_concept_id when 8507 then 'M' when 8532 then 'F' else 'U' end as sex,
        extract(year from f.first_diagnosis_date)::int - p.year_of_birth as age_at_diagnosis
    from first_htn f
    join cdm.person p on p.person_id = f.person_id
)

select
    diagnosis_year,
    sex,
    case
        when age_at_diagnosis < 40 then '<40'
        when age_at_diagnosis < 50 then '40-49'
        when age_at_diagnosis < 60 then '50-59'
        when age_at_diagnosis < 70 then '60-69'
        when age_at_diagnosis < 80 then '70-79'
        else '80+' end                 as age_band,
    count(*)                           as n_patients
from labelled
group by diagnosis_year, sex, age_band
order by diagnosis_year desc, sex, age_band
