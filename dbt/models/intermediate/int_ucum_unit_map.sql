-- Source unit strings (Synthea observation 'units') -> UCUM concept_id. Falls back to
-- any UCUM concept whose code equals the source string. Non-UCUM unit strings resolve to
-- null and will coalesce to 0 in CDM models.

{{ config(materialized='view') }}

select
    concept_code as source_unit,
    concept_id   as concept_id
from {{ source('vocab', 'concept') }}
where vocabulary_id = 'UCUM' and invalid_reason is null
