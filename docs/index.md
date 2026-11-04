# TraceMap

A documentation-first OMOP CDM v5.4 pipeline with end-to-end provenance.

TraceMap takes synthetic clinical records from two sources, maps them into the OMOP Common Data Model, and keeps every row traceable to the exact line of the exact file it came from. One YAML mapping specification is the source of truth: dbt SQL, dbt tests, these documentation pages and the lineage diagrams are all generated from it.

**Synthetic data only.** TraceMap never uses, stores or sends real patient data.

- See the [mapping specifications](mappings/index.md) for every CDM table.
- See the [whole-project lineage](lineage/project.md) for the source -> target graph.
- See the [architectural decision records](decisions/README.md) for every design choice, with alternatives, in plain English.
- See [Five Safes](five_safes.md) for how the design reflects the Five Safes framework.
