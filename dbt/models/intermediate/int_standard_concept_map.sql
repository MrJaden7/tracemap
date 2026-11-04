-- Maps every (source_vocabulary, source_code) pair in use to its standard concept via
-- concept_relationship 'Maps to'. One row per source code, with the standard concept_id
-- and its domain (for domain routing in CDM models).
--
-- Built as a view so a vocabulary refresh is picked up immediately. If performance ever
-- matters, rematerialise as a table filtered to vocabularies actually used by the specs.

{{ config(materialized='view') }}

with source_concepts as (
    select
        concept_id       as source_concept_id,
        concept_code     as source_code,
        vocabulary_id    as source_vocabulary_id,
        domain_id        as source_domain_id
    from {{ source('vocab', 'concept') }}
),
maps_to as (
    select concept_id_1 as src_id, concept_id_2 as tgt_id
    from {{ source('vocab', 'concept_relationship') }}
    where relationship_id = 'Maps to' and invalid_reason is null
),
standard_concepts as (
    select concept_id as standard_concept_id, domain_id as standard_domain_id
    from {{ source('vocab', 'concept') }}
    where standard_concept = 'S'
)

-- A source concept can have more than one 'Maps to' relationship when the vocabulary
-- authors leave the mapping ambiguous. OMOP convention is to pick one deterministically
-- rather than silently duplicate downstream rows. We take the lowest standard_concept_id
-- per source, documented here so the choice is reviewable.
select distinct on (sc.source_vocabulary_id, sc.source_code)
    sc.source_code,
    sc.source_vocabulary_id,
    sc.source_concept_id,
    sc.source_domain_id,
    std.standard_concept_id,
    std.standard_domain_id
from source_concepts sc
left join maps_to          m   on m.src_id      = sc.source_concept_id
left join standard_concepts std on std.standard_concept_id = m.tgt_id
order by sc.source_vocabulary_id, sc.source_code, std.standard_concept_id nulls last
