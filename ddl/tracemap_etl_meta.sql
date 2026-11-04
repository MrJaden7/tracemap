-- TraceMap's own metadata tables. Kept in etl_meta so the cdm schema stays standard OMOP.

CREATE TABLE IF NOT EXISTS etl_meta.vocabulary_load (
    table_name          varchar(50)  NOT NULL,
    file_name           varchar(255) NOT NULL,
    file_rows           bigint       NOT NULL,
    loaded_rows         bigint       NOT NULL,
    vocabulary_version  varchar(255),
    loaded_at           timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (table_name, loaded_at)
);
