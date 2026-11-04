# ADR 0009: Domain routing

- Status: Proposed (deferred to Phase 2)
- Date: 2026-11-04

## Context

A Synthea *condition* carries a SNOMED code. Mapping that code to its standard concept via `Maps to` may return a concept whose domain is not Condition but, for example, Procedure or Observation. Writing that row into `condition_occurrence` anyway is a common OMOP bug, because queries that trust the domain break.

The correct behaviour (from the OMOP conventions): the destination table is decided by the domain of the mapped standard concept, not by the source table.

## Decision

In Phase 1, every source domain writes to its "natural" CDM table. For example, conditions go to `condition_occurrence` and procedures go to `procedure_occurrence`, even where the mapped standard concept lands in a different domain. The spec records `domain_routing: true` on those fields so Phase 2 can switch the behaviour on without changing the YAML.

In Phase 2, the intermediate layer will:
1. Resolve each row's standard concept and its domain against `vocab.concept`.
2. Route the row into the CDM table whose name matches that domain (Procedure -> `procedure_occurrence`, Observation -> `observation`, Measurement -> `measurement`).
3. Keep the source value and source table in lineage so the move is visible.

## Alternatives considered

- **Do routing in Phase 1.** Would be more correct, but adds a conditional UNION to every event table before the basic pipeline is proven end-to-end. The spec already flags the rule as `domain_routing: true` so no mapping is lost.
- **Route at query time with views.** Hides the routing from readers of the CDM and from OHDSI tools that expect physical tables.

## Consequences

- Phase 1 coverage numbers mildly understate correctness: a SNOMED code that is really a procedure is counted as a condition.
- Phase 2 will re-run coverage and reconciliation after routing is enabled; any change in counts is expected and will be documented.

## In plain English

When a diagnosis code turns out to really mean a procedure, it should go in the procedure table. Phase 1 leaves it in diagnoses so the basic pipeline works; Phase 2 moves it.
