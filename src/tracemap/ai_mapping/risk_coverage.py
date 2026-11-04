"""Risk-coverage curve.

Each method has a notion of 'confidence'. For hybrid, we use the BM25 score. For
llm_rerank_anthropic we use BM25 score of the chosen candidate as a proxy, since the
Anthropic re-ranker already applies its own internal threshold via NO_MATCH (and so
needs no secondary cutoff to achieve its abstention).

For a sweep of BM25-score thresholds, we only accept predictions whose BM25 score is
above the threshold and compute (coverage, precision). A curve of (coverage, precision)
at each threshold shows how precision changes as coverage is forced up or down.

Used by `tracemap ai risk-coverage` to produce docs/ai_mapping/risk_coverage.svg.
"""

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tracemap.ai_mapping.gold import GoldItem, load_test_set
from tracemap.ai_mapping.methods import HybridMethod, LlmReRanker, _build_index
from tracemap.ai_mapping.safety import verify_concept
from tracemap.db import connect


@dataclass(frozen=True)
class CurvePoint:
    threshold: float
    coverage: float
    precision: float
    n_committed: int
    n_correct: int


def _bm25_score_of_candidate(term: str, concept_name: str) -> float:
    """BM25 score of `concept_name`'s tokens against the term query. Cheap approximation."""
    idx = _build_index()
    toks = term.lower().split()
    if not toks:
        return 0.0
    cand_tokens = concept_name.lower().split()
    if not cand_tokens:
        return 0.0
    # idf-weighted token overlap, a monotonic proxy for the true BM25 score of that doc.
    idf = idx.bm25.idf
    return sum(idf.get(t, 0.0) for t in cand_tokens if t in toks)


def _collect_predictions(method, items: list[GoldItem]) -> list[dict]:
    rows = []
    with connect() as conn:
        for item in items:
            pred = method.predict(item.term)
            picked = pred.concept_id
            if picked is not None:
                vr = verify_concept(conn, picked, expected_vocabulary=item.expected_vocabulary)
                if not vr.ok:
                    picked = None
            score = 0.0
            if picked is not None:
                cand = next((c for c in pred.candidates if c.concept_id == picked), None)
                if cand is not None:
                    score = _bm25_score_of_candidate(item.term, cand.concept_name)
            rows.append(
                {
                    "item": item,
                    "picked": picked,
                    "correct": picked is not None and picked == item.expected_concept_id,
                    "score": score,
                }
            )
    return rows


def curve(rows: list[dict], thresholds: list[float]) -> list[CurvePoint]:
    n = len(rows)
    points = []
    for t in thresholds:
        committed = [r for r in rows if r["picked"] is not None and r["score"] >= t]
        correct = [r for r in committed if r["correct"]]
        coverage = len(committed) / n if n else 0.0
        precision = (len(correct) / len(committed)) if committed else 1.0
        points.append(CurvePoint(t, coverage, precision, len(committed), len(correct)))
    return points


def plot_curves(curves: dict[str, list[CurvePoint]], out_path) -> None:
    plt.figure(figsize=(6, 4), dpi=120)
    for name, pts in curves.items():
        xs = [p.coverage for p in pts]
        ys = [p.precision for p in pts]
        plt.plot(xs, ys, marker=".", label=name)
    plt.xlabel("Coverage (fraction of test items the method committed to)")
    plt.ylabel("Precision (correct / committed)")
    plt.title("Risk-coverage curve, test set, BM25-score threshold sweep")
    plt.xlim(0, 1)
    plt.ylim(0, 1.02)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def build_default_curve() -> dict:
    items = load_test_set()
    thresholds = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    hybrid_rows = _collect_predictions(HybridMethod(top_k=10), items)
    llm_rows = _collect_predictions(LlmReRanker(mode="anthropic"), items)
    return {
        "hybrid": curve(hybrid_rows, thresholds),
        "llm_rerank_anthropic": curve(llm_rows, thresholds),
    }
