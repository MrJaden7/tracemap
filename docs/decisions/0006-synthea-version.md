# ADR 0006: Synthea version

- Status: Accepted
- Date: 2026-11-04

## Context

Synthea generates the primary synthetic source. In Phase 2 the same Synthea output will also be run through OHDSI's reference ETL (`ETL-Synthea`), and TraceMap's CDM will be reconciled against that reference. The two ETLs must therefore agree on Synthea's schema.

As of 4 November 2026:

- **Synthea** has released up to **v4.0.0** (March 2026); current master is tagged `master-branch-latest` (October 2026).
- **ETL-Synthea** latest release is **v2.1.1** (March 2026). Its README lists supported Synthea versions as 2.7.0 (the example), 3.0.0, 3.1.0, 3.2.0 and **3.3.0**. Versions 3.4.0 and 4.0.0 are not listed.

## Decision

Pin **Synthea v3.3.0** with **seed 42** throughout the project. Pin **ETL-Synthea v2.1.1** for Phase 2.

The Synthea jar used is `synthea-with-dependencies.jar` from the v3.3.0 release. It is downloaded by `tracemap synthea fetch` into `data/synthea/jar/` (gitignored), with a SHA-256 checksum recorded in `etl_meta` at generation time.

The Synthea generation command is:

```
java -jar synthea-with-dependencies.jar -p 5000 -s 42 \
     --exporter.csv.export true --exporter.fhir.export false \
     --exporter.baseDirectory ./data/synthea/output
```

A 200-patient sample is generated separately with seed 42 for use in CI and fast local testing.

## Alternatives considered

- **Latest release (v4.0.0):** newer features, but outside ETL-Synthea's supported list. A difference between TraceMap and the reference ETL could then be caused by TraceMap, by ETL-Synthea, or by a schema change between Synthea versions. That ambiguity would weaken the reconciliation evidence.
- **Master `master-branch-latest`:** moves with Synthea's `master`, which breaks reproducibility.
- **v3.2.0 or older:** supported, but further behind the current release than needed.

## Consequences

- The Synthea version, seed and jar checksum are recorded in `etl_meta.cdm_run` and written to `CDM_SOURCE` on every build, so the exact source of the data is always traceable.
- If ETL-Synthea adds support for v3.4.0 or v4.0.0 before Phase 2, a new ADR can supersede this one and the bump is a one-line change.

## In plain English

Synthea has moved on to version 4, but the reference tool TraceMap will be compared against only supports up to version 3.3.0. Picking the newest version both tools agree on means every difference between them is a difference in how the ETL works, not a difference in the input data.
