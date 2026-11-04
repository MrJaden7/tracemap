-- Overrides the generator's stub. Mapping: mapping_spec/metadata.yml v0.1.0.
-- One row per metadata item describing the latest completed run.

{{ config(materialized='table', schema='cdm', alias='metadata') }}

with latest_run as (
    select run_id, finished_at, git_commit, synthea_version, synthea_seed,
           synthea_jar_sha256, vocabulary_version, spec_version
    from {{ source('etl_meta', 'cdm_run') }}
    where status = 'completed'
    order by started_at desc
    limit 1
),
items as (
    select 1 as metadata_id, 'etl_version' as name,
           'tracemap v0.1.0 ('||coalesce(git_commit, 'local')||')' as value_as_string,
           finished_at::date as metadata_date
    from latest_run
    union all select 2, 'synthea_version',    synthea_version,          finished_at::date from latest_run
    union all select 3, 'synthea_seed',       synthea_seed::text,       finished_at::date from latest_run
    union all select 4, 'synthea_jar_sha256', synthea_jar_sha256,       finished_at::date from latest_run
    union all select 5, 'vocabulary_version', vocabulary_version,       finished_at::date from latest_run
    union all select 6, 'spec_version',       coalesce(spec_version, '0.1.0'), finished_at::date from latest_run
)

select
    metadata_id,
    0                           as metadata_concept_id,
    0                           as metadata_type_concept_id,
    name,
    value_as_string,
    null::integer               as value_as_concept_id,
    metadata_date,
    null::timestamp             as metadata_datetime,
    null::text                  as value_as_number
from items
