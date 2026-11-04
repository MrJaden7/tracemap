# Five Safes

TraceMap is a portfolio project, not a Secure Data Environment. It still demonstrates how the Five Safes framework shapes design decisions, because every Phase 2 feature is built with the framework in mind.

## Safe data

- All patient records are synthetic (Synthea, plus TraceMap's own UK extract generator). No real patient data is ever used.
- Source patient identifiers are pseudonymised before they reach the CDM: a HMAC-SHA256 key derived from a secret salt, loaded from the environment, is used to produce the cross-source linkage identifier. The salt is never committed and never logged.
- The CDM stores only pseudonymised source values; original Synthea UUIDs are kept only in `etl_meta.person_key_map`, which never leaves the warehouse in exports.

## Safe projects

- The pipeline exposes one entry point (`tracemap build`) and one documented set of mappings. A researcher cannot change the mapping without an ADR and a review.
- All mapping rules are declared in `mapping_spec/` YAML. A change is a code review change.

## Safe people

- Not enforced here. In a real SDE, access to `cdm.*` schemas is granted by role, and researcher accounts never see `raw.*` or `etl_meta.*`.
- TraceMap documents the separation (schemas `raw`, `etl_meta`, `vocab`, `cdm`) that a real SDE's row-level security would enforce.

## Safe settings

- Local only. The pipeline runs in a single developer environment inside Docker. No internet access is required once the vocabularies and Synthea jar are downloaded.
- Vocabularies are licensed and are never committed; the README names the Athena account path needed to fetch them.

## Safe outputs

- Every cohort query (Phase 2) runs through an output checker that applies small-number suppression and rounding (defaults: suppress counts below 10, round to the nearest 5, suppress percentages that would reveal a suppressed count).
- Thresholds live in `config/output_rules.yml` so a different environment can apply its own rules without editing the queries.
- A before-and-after example lives alongside the queries so reviewers can see exactly what is suppressed.

## What a real SDE would add

- Row-level security tied to researcher accounts.
- Logged egress; every output the researcher downloads goes through a named approver.
- Encryption at rest and in transit, with keys managed outside the application.
- Full disaster-recovery and retention policies.
- A documented five-safes-aligned governance process, not just technical controls.
