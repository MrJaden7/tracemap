-- Non-numeric result values (Synthea observation 'value' strings) -> SNOMED concept_id.
-- Matched on exact concept_name (case-insensitive). A rough starting point that covers
-- common survey responses like 'Yes', 'No', 'Never'; refined in Phase 2.

{{ config(materialized='view') }}

select
    lower(concept_name) as source_value,
    concept_id          as concept_id
from {{ source('vocab', 'concept') }}
where vocabulary_id = 'SNOMED'
  and standard_concept = 'S'
  and invalid_reason is null
