-- TraceMap's own metadata tables. Kept in etl_meta and raw so the cdm schema stays standard OMOP.

CREATE TABLE IF NOT EXISTS etl_meta.vocabulary_load (
    table_name          varchar(50)  NOT NULL,
    file_name           varchar(255) NOT NULL,
    file_rows           bigint       NOT NULL,
    loaded_rows         bigint       NOT NULL,
    vocabulary_version  varchar(255),
    loaded_at           timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (table_name, loaded_at)
);

-- One row per end-to-end ETL run. Written at the start, updated at the end.
CREATE TABLE IF NOT EXISTS etl_meta.cdm_run (
    run_id             bigserial   PRIMARY KEY,
    started_at         timestamptz NOT NULL DEFAULT now(),
    finished_at        timestamptz,
    git_commit         text,
    synthea_version    text,
    synthea_seed       integer,
    synthea_jar_sha256 text,
    vocabulary_version text,
    spec_version       text,
    status             text        NOT NULL DEFAULT 'running',
    notes              text
);

-- One row per file loaded into raw. The checksum detects an input file changing.
CREATE TABLE IF NOT EXISTS raw.load_manifest (
    manifest_id      bigserial   PRIMARY KEY,
    run_id           bigint      NOT NULL REFERENCES etl_meta.cdm_run(run_id),
    source_system    text        NOT NULL,
    target_table     text        NOT NULL,
    file_name        text        NOT NULL,
    file_path        text        NOT NULL,
    file_sha256      char(64)    NOT NULL,
    file_size_bytes  bigint      NOT NULL,
    row_count        bigint      NOT NULL,
    loaded_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_load_manifest_run ON raw.load_manifest (run_id);
CREATE INDEX IF NOT EXISTS idx_load_manifest_source_table ON raw.load_manifest (source_system, target_table);

CREATE TABLE IF NOT EXISTS etl_meta.synthea_linkage_keys (
    synthea_id   text PRIMARY KEY,
    linkage_key  text NOT NULL,
    recorded_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS etl_meta.mapping_suggestions (
    suggestion_id      bigserial    PRIMARY KEY,
    created_at         timestamptz  NOT NULL DEFAULT now(),
    source_system      text         NOT NULL,
    source_code        text         NOT NULL,
    source_vocabulary  text,
    suggested_concept_id bigint,
    status             text         NOT NULL DEFAULT 'pending',
    reason             text,
    method             text,
    reviewer           text,
    reviewed_at        timestamptz,
    notes              text
);
