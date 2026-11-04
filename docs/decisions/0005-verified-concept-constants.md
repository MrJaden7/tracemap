# ADR 0005: Hard-coded concept IDs are verified against the vocabulary

- Status: Accepted
- Date: 2026-11-04

## Context

Almost every concept ID in TraceMap is looked up from the vocabulary at run time. A few well-known ones are used directly in code or mapping rules, for example the gender, visit and record-type concepts. A wrong constant would silently mislabel every affected row.

## Decision

All hard-coded concept IDs live in one module, `src/tracemap/constants.py`. Each records not just the ID but the name, domain and vocabulary it must have:

| concept_id | Name | Domain | Vocabulary |
|---|---|---|---|
| 0 | No matching concept | Metadata | None |
| 8507 | MALE | Gender | Gender |
| 8532 | FEMALE | Gender | Gender |
| 9201 | Inpatient Visit | Visit | Visit |
| 9202 | Outpatient Visit | Visit | Visit |
| 9203 | Emergency Room Visit | Visit | Visit |
| 32817 | EHR | Type Concept | Type Concept |

`tests/integration/test_constants.py` checks each against the loaded `vocab.concept` table: the ID must exist, the name, domain and vocabulary must match, and every non-zero constant must be a standard concept. A wrong constant fails the build.

All seven were checked against release v5.0 29-AUG-26 when this ADR was written.

## Alternatives considered

- **Look every concept up by name at run time:** avoids constants entirely, but names are not unique across vocabularies and lookups by name hide intent.
- **Constants without tests:** common in ETL code, and exactly how wrong IDs survive unnoticed.

## Consequences

- Adding a constant means adding it to `constants.ALL`, which automatically adds a test.
- In CI the real vocabulary is not available, so the same test runs against a small fixture vocabulary (Phase 2).

## In plain English

The handful of codes typed directly into the program are each checked against the official dictionary on every test run, so a typo cannot slip through.
