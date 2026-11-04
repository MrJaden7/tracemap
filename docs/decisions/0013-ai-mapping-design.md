# ADR 0013: AI-assisted mapping design

- Status: Accepted
- Date: 2026-11-04

## Context

Phase 3 evaluates whether modern retrieval + a constrained LLM can speed up mapping without compromising correctness. The project's dissertation argument (AI systems answer questions their sources do not support unless they are designed and tested to abstain) applies directly.

## Decision

Four methods are implemented in `src/tracemap/ai_mapping/methods.py`:

1. **ExactMatchMethod**: exact normalised match.
2. **BM25Method**: BM25 over tokenised standard concept names.
3. **HybridMethod**: BM25 + exact match merged, returns top-10 candidates.
4. **LlmReRanker**: picks one of the top-10 candidates or returns NO_MATCH. Two modes: 'deterministic' (offline stub, used in CI) and 'anthropic' (gated on `ANTHROPIC_API_KEY`, verified against the candidate list before acceptance).

Common rules:

- Every chosen concept_id passes through `safety.verify_concept` before being counted correct: must exist, be standard, and match the vocabulary/domain the method declared.
- Abstentions are a first-class result: coverage and correct-abstention are reported alongside accuracy and precision.
- Repeats are run even for deterministic methods, so the standard deviation column always exists and LLM run-to-run variance is comparable to the baseline's zero.

Suggestions never write to `cdm.*`. They land in `etl_meta.mapping_suggestions` for a human reviewer (table is defined in `ddl/tracemap_etl_meta.sql` and is populated by the forthcoming `tracemap ai suggest` command, Phase 3 close-out).

## Alternatives considered

- **Direct LLM mapping (no candidates).** Rejected: the LLM would invent concept_ids, and the safety gate would reject most of them. Constraining to a candidate list makes the task a selection, not a generation.
- **Embedding-only retrieval.** Reasonable, but adds a dependency (sentence-transformers or OpenAI embeddings) without a baseline comparison for why. Phase 3 close-out may add it as a fifth method.
- **Scoring against ground-truth concept_ids only.** Hides the abstention story. Reporting coverage and correct-abstention side by side is a direct consequence of ADR 0010 / the dissertation framing.

## Consequences

- The evaluation harness runs offline and deterministically in CI. Adding a real LLM requires one env var.
- A hostile or buggy LLM cannot poison the CDM: the safety gate stops it, and the reviewer catches what survives.
- The evaluation can be re-run on any schedule to track drift.

## In plain English

The AI has two jobs: pick the right candidate, and know when to say no. Both are measured. The CDM is never touched by the AI; a reviewer decides what becomes a real mapping.
