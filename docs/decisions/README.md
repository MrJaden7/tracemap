# Architecture Decision Records

Each significant design choice in TraceMap is recorded as a numbered ADR: the context, the decision, the alternatives that were considered, and the consequences.

An ADR is never edited to change its decision. If a decision changes, a new ADR supersedes the old one and the old one's status is updated to point at it.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-repository-layout-and-tooling.md) | Repository layout and tooling | Accepted |
| [0002](0002-separate-vocab-schema.md) | Keep vocabulary tables in a separate vocab schema | Accepted |
| [0003](0003-vocabulary-selection.md) | Vocabulary selection and release | Accepted |
| [0004](0004-vocabulary-loading.md) | How vocabularies are loaded and verified | Accepted |
| [0005](0005-verified-concept-constants.md) | Hard-coded concept IDs are verified against the vocabulary | Accepted |
| [0006](0006-synthea-version.md) | Synthea version pinned to v3.3.0 | Accepted |
| [0007](0007-raw-loading-and-provenance.md) | Raw loading, run tracking and provenance | Accepted |
| [0008](0008-dbt-and-generator.md) | dbt layout and the generator | Accepted |
| [0009](0009-domain-routing.md) | Domain routing | Proposed (Phase 2) |
| [0010](0010-row-lineage.md) | Row lineage and the trace command | Accepted |
| [0011](0011-mapping-coverage.md) | Mapping coverage reporting | Accepted |
| [0012](0012-uk-extract-and-linkage.md) | UK synthetic extract and pseudonymised linkage | Accepted |
| [0013](0013-ai-mapping-design.md) | AI-assisted mapping design | Accepted |
