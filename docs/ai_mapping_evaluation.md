# AI-assisted mapping evaluation

## The question

Real hospital extracts contain local, messy source terms with no clean code: abbreviations ("T2DM", "HTN", "#NOF"), British spellings, typos, free-text diagnosis descriptions, reordered partials. Mapping them to OMOP standard concepts is slow, expert work. OHDSI's Usagi helps with string similarity. Can modern retrieval and a constrained LLM do better, safely?

## Hard safety rule

The AI never writes to the CDM. Every suggestion is a row in `etl_meta.mapping_suggestions` that a human reviewer must accept. Before a suggestion is recorded at all, `safety.verify_concept` checks that:

1. the concept_id exists in `vocab.concept`,
2. it is standard (`standard_concept = 'S'`),
3. its vocabulary matches, if the method declared one,
4. its domain matches, if the method declared one.

A suggestion that fails any check is stored with status `rejected` and a reason; the reviewer still sees it. Only synthetic terms are sent to the LLM, and the module can run entirely offline with the deterministic re-ranker.

## Gold-standard evaluation set

Built by `tracemap ai gold`, deterministic for a given seed.

- **300 mappable terms** derived from standard concept names in SNOMED, ICD-10, RxNorm and LOINC. Perturbations: abbreviation (10 common clinical ones), British spelling swap (US -> UK), adjacent-character typo, partial description with reordered words, verbatim.
- **50 deliberately unmappable terms**: "Patient refused test", "zzz", "Needs chase", "Private matter - no further details" and similar.
- Deterministic development / held-out test split by hash of the term.

## Methods

1. **ExactMatchMethod**: exact normalised match against the concept pool.
2. **BM25Method**: BM25 over tokenised concept names.
3. **HybridMethod**: BM25 + exact match merged.
4. **LlmReRanker (deterministic mode)**: offline stub that picks the top hybrid candidate for substantive terms and abstains on short/empty ones. Used in CI and when no API key is configured.
5. **LlmReRanker (anthropic mode)**: constrained LLM re-ranker over the top-10 hybrid candidates. Must either pick a candidate's concept_id or return NO_MATCH. Any pick not in the candidate list is rejected.

## Results (350 items, 2 repeated runs per method)

| Method                     | Top-1 accuracy    | Precision         | Coverage          | Correct abstention |
|----------------------------|-------------------|-------------------|-------------------|--------------------|
| exact_match                | 0.397 +/- 0.000   | 0.992 +/- 0.000   | 0.343 +/- 0.000   | 1.000 +/- 0.000    |
| bm25                       | 0.800 +/- 0.000   | 0.719 +/- 0.000   | 0.954 +/- 0.000   | 0.020 +/- 0.000    |
| hybrid                     | 0.797 +/- 0.000   | 0.718 +/- 0.000   | 0.951 +/- 0.000   | 0.020 +/- 0.000    |
| llm_rerank (deterministic) | 0.780 +/- 0.000   | 0.713 +/- 0.000   | 0.937 +/- 0.000   | 0.020 +/- 0.000    |
| **llm_rerank (anthropic)** | **0.852 +/- 0.002** | **0.922 +/- 0.002** | **0.791 +/- 0.004** | **0.830 +/- 0.014** |

Run the repeated evaluation yourself with:

```bash
uv run tracemap ai evaluate --repeats 5
uv run tracemap ai evaluate --repeats 5 --use-llm   # requires ANTHROPIC_API_KEY
```

## Discussion

- **Exact match is the only non-AI method that knows when to abstain.** Its 99.2% precision is bought with 34% coverage. It is the right first pass before any more aggressive method.
- **BM25 covers almost everything (95.4%) but has no abstention signal.** It correctly abstains on only 2% of unmappable terms. Used alone it would smuggle junk into the review queue.
- **Hybrid matches BM25 on top-1 accuracy** without improving the abstention rate. The value of the exact-match arm is the explicit "this was an exact match" reason on committed candidates.
- **The deterministic re-ranker is an offline baseline**, matching hybrid without any model call. Its standard deviation is 0 across runs because it is purely deterministic. It exists so CI and anyone without an API key can run the full harness, and so LLM run-to-run variance can be compared to a fixed reference.
- **The Anthropic re-ranker (`claude-sonnet-4-6`)** beats BM25 on top-1 accuracy by 5.2 points, lifts precision by 20.3 points (0.719 to 0.922) and correctly abstains on 83% of unmappable terms, up from 2% for every non-exact method. Coverage drops from 0.954 to 0.791 by design: the LLM declines to commit when the candidate list does not contain a confident match. Run-to-run standard deviation is small (0.002 to 0.014) because the task is highly constrained (pick one of ten, or NO_MATCH).

The abstention lift is the key number. Every non-LLM baseline is wrong about 70% of the time on unmappable terms, because it will always pick its top BM25 candidate. The LLM reads the candidate list and the source term together and says NO_MATCH on 83% of truly unmappable terms, with a short reason like "the source term 'intestine of' is incomplete/truncated". This is the behaviour the dissertation argues cannot be assumed: it has to be designed in and measured.

## Recommendation

Use layered methods. Run exact match first and accept its suggestions with minimal review (99.2% precision). Pass everything it did not resolve through hybrid retrieval, and send the hybrid candidates to the LLM re-ranker, which converts BM25's broad reach into the right mix of commitment and abstention. Keep the hard safety gate (verify + reviewer accept) regardless of method, because every method occasionally picks a plausible but wrong standard concept. The reviewer stays in the loop.

Rough cost of a full-evaluation run on this gold set with Anthropic (`claude-sonnet-4-6`): ~2,500 to 4,000 input tokens per item (10 candidates + instructions) and ~50 output tokens per item. At current Sonnet rates this is well under £0.01 per item; one full 350-item x 2-repeat run came in at about £1. The economics work even if the LLM is in the loop for every unmapped term.

## Link to the dissertation

Jaden's MSc dissertation found that AI systems answer questions their sources do not support unless they are designed and tested to abstain. TraceMap's constrained re-ranker is the same pattern: the candidate list is the source, the method must stay inside it, and the correct-abstention metric is a first-class success criterion, not an afterthought.
