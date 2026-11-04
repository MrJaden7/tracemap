# ADR 0002: Keep vocabulary tables in a separate vocab schema

- Status: Accepted
- Date: 2026-11-04

## Context

The official OHDSI CDM v5.4 PostgreSQL DDL (`ddl/OMOPCDM_postgresql_5.4_*.sql`, copied unchanged from OHDSI/CommonDataModel) puts all 39 tables, clinical and vocabulary, under one placeholder schema, `@cdmDatabaseSchema`.

TraceMap's architecture separates them: clinical data in `cdm`, vocabularies in `vocab`. The OMOP conventions allow this. OHDSI tools such as the Data Quality Dashboard take a separate `vocabDatabaseSchema` parameter.

## Decision

Keep the OHDSI DDL files byte for byte as published, and route each statement at apply time (`src/tracemap/load/ddl.py`):

- The 10 vocabulary tables (`concept`, `vocabulary`, `domain`, `concept_class`, `concept_relationship`, `relationship`, `concept_synonym`, `concept_ancestor`, `source_to_concept_map`, `drug_strength`) go to `vocab`.
- The other 29 tables go to `cdm`.
- References inside a statement are routed by table, so a foreign key from `cdm.person` to the concept table correctly points at `vocab.concept`.

## Alternatives considered

- **Everything in one schema:** matches the DDL directly, but mixes licensed reference data (reloaded on each Athena release) with ETL output (rebuilt on each run). Rebuilding the CDM would mean working around 5 GB of vocabulary.
- **Hand-editing the DDL:** simple, but the DDL could then no longer be compared with the official version, which weakens the claim that the CDM is conformant.

## Consequences

- The CDM can be dropped and rebuilt without touching the vocabularies, and the vocabularies can be upgraded without touching the CDM.
- Unit tests check that no `@cdmDatabaseSchema` placeholder survives routing and that every Phase 1 table is created.
- OHDSI tools must be given both schemas (`cdm` and `vocab`).

## In plain English

The reference dictionaries and the patient data live in separate drawers, so either can be replaced without disturbing the other. The official table definitions are used exactly as published.
