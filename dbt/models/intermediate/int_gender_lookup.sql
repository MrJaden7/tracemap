-- Resolves Synthea gender strings (M, F) to OMOP Gender concepts (8507, 8532) at build
-- time against the loaded vocabulary. Kept separate from the person model so tests can
-- assert the resolution independently.

{{ config(materialized='view') }}

select
    source_code,
    concept_id as gender_concept_id,
    concept_name as gender_concept_name
from (
    select 'M' as source_code union all select 'F'
) codes
left join {{ source('vocab', 'concept') }} c
    on c.vocabulary_id = 'Gender'
    and c.standard_concept = 'S'
    and c.concept_code = codes.source_code
