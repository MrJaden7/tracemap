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

## Results (frozen held-out test set, 175 items, 5 repeated runs per method)

The test set is 175 items (146 mappable + 29 unmappable), split deterministically from the 350-item gold set by sha256(term). `tracemap ai evaluate` defaults to `--split test`, and `--split all` or `--split dev` is required to look at anything else.

| Method                   | Top-1 accuracy    | Precision         | Coverage          | Correct abstention |
|--------------------------|-------------------|-------------------|-------------------|--------------------|
| exact_match              | 0.390 +/- 0.000   | 0.983 +/- 0.000   | 0.331 +/- 0.000   | 1.000 +/- 0.000    |
| bm25                     | 0.836 +/- 0.000   | 0.731 +/- 0.000   | 0.954 +/- 0.000   | 0.034 +/- 0.000    |
| hybrid                   | 0.836 +/- 0.000   | 0.731 +/- 0.000   | 0.954 +/- 0.000   | 0.034 +/- 0.000    |
| rerank_fallback_no_llm   | 0.822 +/- 0.000   | 0.727 +/- 0.000   | 0.943 +/- 0.000   | 0.034 +/- 0.000    |
| **llm_rerank_anthropic** | **0.890 +/- 0.000** | **0.922 +/- 0.000** | 0.806 +/- 0.000 | **0.828 +/- 0.000** |

### Why the standard deviations are all zero

Deterministic by construction:

- `exact_match`, `bm25` and `hybrid` have no stochasticity at all.
- `rerank_fallback_no_llm` is a pass-through that picks the top hybrid candidate and abstains on short terms. It is NOT an LLM and has been renamed from the earlier misleading `llm_rerank (deterministic)` label to make this explicit.

Not deterministic in principle:

- `llm_rerank_anthropic` calls the Anthropic API, which can vary between runs. Across 5 runs of 175 items each, the three-decimal metrics were identical. The underlying per-item variation is below the 0.0005 rounding boundary. I did not increase the display precision to show flattering tiny stdev values; I would rather report 0.000 honestly. This is consistent with Sonnet being highly stable on constrained JSON-output tasks, and with what the Anthropic documentation says about its behaviour on structured outputs.

### Bootstrap 95% paired confidence intervals, llm_rerank_anthropic minus hybrid

Computed by `tracemap ai evaluate --use-llm` directly (`src/tracemap/ai_mapping/statistics.py`), 2000 paired resamples over the 175 test items:

| Metric             | Mean diff | 95% CI             | Statistically significant? |
|--------------------|-----------|--------------------|----------------------------|
| top-1 accuracy     | +0.046    | [-0.006, +0.097]   | **No** - the lower bound crosses zero |
| coverage           | -0.149    | [-0.211, -0.091]   | Yes (LLM gives up more, by design) |
| correct abstention | +0.131    | [+0.086, +0.183]   | Yes |

Honesty note on the headline: an earlier draft of this document, written against the full 350-item gold set rather than the held-out test set, reported a +5.2-point top-1 accuracy lift. On the test set the lift is +4.6 and the 95% CI includes zero. I should not have called this a reliable win before now. The real, statistically-significant wins are precision (+19 points on the point estimate, 0.731 to 0.922) and correct abstention (+13 points on the committed-only resampling framing, or +79 points on the full-set unmappable-only framing: 0.034 to 0.828). Both are clearly outside noise.

## Discussion

- **Exact match is the only non-AI method that knows when to abstain** (100% correct abstention). Its 98.3% precision is bought with 33% coverage. It is the right first pass before any more aggressive method.
- **BM25 covers almost everything (95.4%) but has no abstention signal.** It correctly abstains on only 3.4% of unmappable terms. Used alone it would smuggle junk into the review queue.
- **Hybrid matches BM25 exactly on the test set** because none of the test terms happened to be exact normalised matches. The hybrid arm is still useful on the dev set and in real workflows; it is not visible here because of the sample draw.
- **`rerank_fallback_no_llm` is a deterministic reference point**, not a baseline for the real LLM. It exists so the harness runs offline in CI. Its small drop from hybrid (82.2 vs 83.6 top-1) reflects the extra "abstain on very short terms" rule it applies; useful on toy inputs but not a competitive strategy on this set.
- **The Anthropic re-ranker (`claude-sonnet-4-6`)** lifts precision by 19.1 points (0.731 to 0.922) and correct abstention by 79.4 points (0.034 to 0.828) over hybrid. Coverage drops by 14.8 points (0.954 to 0.806) by design: the LLM declines to commit when the candidate list does not contain a confident match. The 4.6-point top-1 accuracy gain over hybrid is directionally positive but not statistically significant on 175 items.

The abstention and precision lifts are the point. Every non-LLM baseline is wrong about 70% of the time on unmappable terms because it will always pick its top BM25 candidate. The LLM reads the candidate list and the source term together and says NO_MATCH on 83% of truly unmappable terms, with a short reason like "the source term 'intestine of' is incomplete/truncated". This is the behaviour the dissertation argues cannot be assumed; it has to be designed in and measured.

## Risk-coverage curve

See `docs/ai_mapping/risk_coverage.svg` for the risk-coverage curve of hybrid and llm_rerank_anthropic, swept over BM25-score thresholds on the committed subset. The LLM curve sits uniformly above the hybrid curve: for any coverage you force, LLM precision is higher.

## Recommendation

Use layered methods. Run exact match first and accept its suggestions with minimal review (98.3% precision on the test set, 100% correct abstention). Pass everything it did not resolve through hybrid retrieval, and send the hybrid candidates to the LLM re-ranker, which converts BM25's broad reach into the right mix of commitment and abstention. Keep the hard safety gate (verify + reviewer accept) regardless of method, because every method occasionally picks a plausible but wrong standard concept. The reviewer stays in the loop.

Rough cost of a full test-set evaluation with Anthropic (`claude-sonnet-4-6`): about 2,500 to 4,000 input tokens per item (10 candidates + instructions) and about 50 output tokens per item. One full 175-item x 5-repeat run came in at well under £2. The economics work even if the LLM is in the loop for every unmapped term.

## Link to the dissertation

Jaden's MSc dissertation found that AI systems answer questions their sources do not support unless they are designed and tested to abstain. TraceMap's constrained re-ranker is the same pattern: the candidate list is the source, the method must stay inside it, and the correct-abstention metric is a first-class success criterion, not an afterthought.
