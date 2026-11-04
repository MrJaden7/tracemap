-- (source_vocabulary_id, source_code) -> source_concept_id. Same shape as
-- int_standard_concept_map but does not follow the 'Maps to' relationship, so the
-- original source concept is kept as source_concept_id in CDM columns.

{{ config(materialized='view') }}

select
    concept_id    as source_concept_id,
    concept_code  as source_code,
    vocabulary_id as source_vocabulary_id,
    domain_id     as source_domain_id
from {{ source('vocab', 'concept') }}
