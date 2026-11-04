"""Mapping methods to evaluate.

- ExactMatchMethod: exact and normalised string match against concept + concept_synonym.
- BM25Method:       BM25 over tokenised names and synonyms, top-1.
- HybridMethod:     BM25 + exact match merged, top-k candidates; wraps a re-ranker.
- LlmReRanker:      sees the source term + top-10 candidates and picks one or NO_MATCH.
                     Constrained to the candidate list so it cannot invent concept_ids.
                     Supports a 'deterministic' stub that picks the top BM25 candidate.
                     Real LLM mode is gated on ANTHROPIC_API_KEY being set.

Every Method returns a Prediction with concept_id (None for abstain) and a reason. The
evaluation code applies the safety gate to every non-None concept_id before scoring.
"""

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from rank_bm25 import BM25Okapi

MODEL_ID = os.environ.get("TRACEMAP_LLM_MODEL", "claude-sonnet-4-6")

WORD_RE = re.compile(r"[a-z0-9]+")


def _normalise(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


@dataclass(frozen=True)
class Candidate:
    concept_id: int
    concept_name: str
    vocabulary_id: str
    domain_id: str


@dataclass(frozen=True)
class Prediction:
    concept_id: int | None
    reason: str
    candidates: list[Candidate]


class Method(Protocol):
    name: str

    def predict(self, term: str) -> Prediction: ...


@lru_cache(maxsize=1)
def _load_candidate_pool(limit: int = 50_000) -> list[Candidate]:
    """Pull a pool of standard concepts and their synonyms, tokenised once."""
    from tracemap.db import connect

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT concept_id, concept_name, vocabulary_id, domain_id
            FROM vocab.concept
            WHERE vocabulary_id IN ('SNOMED', 'ICD10', 'RxNorm', 'LOINC')
              AND standard_concept = 'S'
              AND invalid_reason IS NULL
              AND length(concept_name) BETWEEN 3 AND 150
            ORDER BY concept_id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [Candidate(int(r[0]), r[1], r[2], r[3]) for r in rows]


@dataclass
class _Index:
    bm25: BM25Okapi
    candidates: list[Candidate]
    tokens: list[list[str]]
    by_normalised: dict[str, Candidate]


@lru_cache(maxsize=1)
def _build_index() -> _Index:
    pool = _load_candidate_pool()
    tokens = [_normalise(c.concept_name).split() for c in pool]
    bm25 = BM25Okapi(tokens)
    by_norm = {_normalise(c.concept_name): c for c in pool}
    return _Index(bm25=bm25, candidates=pool, tokens=tokens, by_normalised=by_norm)


class ExactMatchMethod:
    name = "exact_match"

    def predict(self, term: str) -> Prediction:
        idx = _build_index()
        key = _normalise(term)
        hit = idx.by_normalised.get(key)
        if hit is None:
            return Prediction(None, "no exact match", [])
        return Prediction(hit.concept_id, "exact normalised match", [hit])


class BM25Method:
    name = "bm25"
    top_k: int = 10

    def __init__(self, top_k: int = 10):
        self.top_k = top_k

    def predict(self, term: str) -> Prediction:
        idx = _build_index()
        toks = _normalise(term).split()
        if not toks:
            return Prediction(None, "empty tokens", [])
        scores = idx.bm25.get_scores(toks)
        order = scores.argsort()[::-1][: self.top_k]
        candidates = [idx.candidates[i] for i in order]
        if not candidates or scores[order[0]] <= 0:
            return Prediction(None, "no BM25 candidate", [])
        return Prediction(
            candidates[0].concept_id, f"BM25 score {scores[order[0]]:.2f}", candidates
        )


class HybridMethod:
    """BM25 + exact match merged. Returns top-k candidates and the exact match (if any)
    as the chosen concept, else the top BM25 candidate."""

    name = "hybrid"

    def __init__(self, top_k: int = 10):
        self.bm25 = BM25Method(top_k=top_k)
        self.exact = ExactMatchMethod()

    def predict(self, term: str) -> Prediction:
        exact = self.exact.predict(term)
        bm = self.bm25.predict(term)
        merged: list[Candidate] = []
        seen = set()
        if exact.concept_id is not None:
            for c in exact.candidates:
                if c.concept_id not in seen:
                    merged.append(c)
                    seen.add(c.concept_id)
        for c in bm.candidates:
            if c.concept_id not in seen:
                merged.append(c)
                seen.add(c.concept_id)
        chosen = exact.concept_id if exact.concept_id is not None else bm.concept_id
        reason = "exact match" if exact.concept_id is not None else bm.reason
        return Prediction(chosen, reason, merged)


LLM_SYSTEM_PROMPT = (
    "You are mapping a messy clinical source term to an OMOP standard concept.\n"
    "You will see 10 candidate concepts. Pick exactly one by its concept_id, or return "
    "NO_MATCH if none is a close match. Do not invent concept_ids. "
    'Return a JSON object: {"concept_id": <int or null>, "reason": "<short>"}.'
)


class RerankFallbackNoLlm:
    """Deterministic fallback that re-ranks the hybrid candidates WITHOUT calling any LLM.

    This method exists only so the evaluation harness runs offline and in CI without an
    API key. It picks the top hybrid candidate for substantive terms and abstains for
    very short or empty-token terms. It is NOT an LLM, NOT a mock of an LLM, and NOT a
    baseline for the real LLM re-ranker. It is a deterministic reference point at the
    same pipeline position where the real LLM would sit.
    """

    name = "rerank_fallback_no_llm"

    def __init__(self):
        self.hybrid = HybridMethod(top_k=10)

    def predict(self, term: str) -> Prediction:
        base = self.hybrid.predict(term)
        if not base.candidates:
            return Prediction(None, "no candidates", [])
        toks = _normalise(term).split()
        if len(toks) < 2:
            return Prediction(None, "no_llm_fallback: short term", base.candidates)
        return Prediction(base.candidates[0].concept_id, "no_llm_fallback: top-1", base.candidates)


class LlmReRanker:
    """LLM-based re-ranker, constrained to the candidate list.

    Calls the Anthropic API with the term and 10 hybrid candidates. Requires
    ANTHROPIC_API_KEY. Verifies the chosen concept_id appears in the candidates before
    accepting it; otherwise returns NO_MATCH with reason.
    """

    name = "llm_rerank_anthropic"

    def __init__(self, mode: str = "anthropic"):
        if mode != "anthropic":
            raise ValueError(
                "LlmReRanker only supports mode='anthropic'. "
                "Use RerankFallbackNoLlm for the offline deterministic fallback."
            )
        self.mode = mode
        self.hybrid = HybridMethod(top_k=10)

    def predict(self, term: str) -> Prediction:
        base = self.hybrid.predict(term)
        if not base.candidates:
            return Prediction(None, "no candidates", [])
        return self._predict_anthropic(term, base.candidates)

    def _predict_anthropic(self, term: str, candidates: list[Candidate]) -> Prediction:
        try:
            import anthropic  # local import so the module loads without the SDK installed
        except ImportError:
            return Prediction(None, "anthropic SDK not installed", candidates)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return Prediction(None, "ANTHROPIC_API_KEY not set", candidates)

        client = anthropic.Anthropic()
        cand_lines = "\n".join(
            f"- {c.concept_id}  {c.concept_name}  ({c.vocabulary_id}, {c.domain_id})"
            for c in candidates
        )
        prompt = f"Source term: {term!r}\n\nCandidates:\n{cand_lines}\n\nReturn JSON only."
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=200,
            system=LLM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return Prediction(None, f"LLM returned non-JSON: {text[:60]!r}", candidates)
        concept_id = data.get("concept_id")
        reason = str(data.get("reason", "")).strip()
        if concept_id is None:
            return Prediction(None, reason or "LLM abstained", candidates)
        try:
            cid = int(concept_id)
        except (TypeError, ValueError):
            return Prediction(None, f"LLM returned invalid concept_id: {concept_id!r}", candidates)
        if cid not in {c.concept_id for c in candidates}:
            return Prediction(None, f"LLM invented concept_id {cid} not in candidates", candidates)
        return Prediction(cid, reason or "LLM pick", candidates)
