"""Evaluation harness.

Runs every method against the gold set and reports:
  - top-1 accuracy on mappable terms
  - precision (correct / committed)
  - coverage (committed / total)
  - correct-abstention rate on unmappable terms
  - mean and standard deviation over `repeats` runs
  - a short risk-coverage curve as a list of (threshold, precision, coverage) tuples
    based on BM25 score cutoffs. Deterministic methods trivially have the same answer
    on each repeat, but the harness still runs the loop so LLM variability shows up.
"""

import statistics
from dataclasses import dataclass

from tracemap.ai_mapping.gold import GoldItem, load_gold_set
from tracemap.ai_mapping.methods import Method, Prediction
from tracemap.ai_mapping.safety import verify_concept
from tracemap.db import connect


@dataclass(frozen=True)
class _PerItemResult:
    item: GoldItem
    prediction: Prediction
    predicted_concept_id: int | None
    safe: bool


@dataclass(frozen=True)
class EvaluationResult:
    method: str
    n_total: int
    n_mappable: int
    n_unmappable: int
    top1_accuracy: float
    precision: float
    coverage: float
    correct_abstention_rate: float


class Evaluation:
    def __init__(self, items: list[GoldItem]):
        self.items = items
        # Per-method per-item outcome arrays, used for bootstrap CIs. Keyed by method name.
        self._outcomes: dict[str, list] = {}

    def run(self, method: Method) -> EvaluationResult:
        results: list[_PerItemResult] = []
        with connect() as conn:
            for item in self.items:
                prediction = method.predict(item.term)
                safe = True
                picked = prediction.concept_id
                if picked is not None:
                    vr = verify_concept(conn, picked, expected_vocabulary=item.expected_vocabulary)
                    if not vr.ok:
                        safe = False
                        picked = None
                results.append(_PerItemResult(item, prediction, picked, safe))

        mappable = [r for r in results if r.item.expected_concept_id is not None]
        unmappable = [r for r in results if r.item.expected_concept_id is None]

        committed = [r for r in results if r.predicted_concept_id is not None]
        correct = [r for r in committed if r.predicted_concept_id == r.item.expected_concept_id]
        abstained_on_unmappable = [r for r in unmappable if r.predicted_concept_id is None]

        total = len(results)
        n_mappable = len(mappable)
        n_unmappable = len(unmappable)
        correct_top1 = sum(
            1 for r in mappable if r.predicted_concept_id == r.item.expected_concept_id
        )

        # Persist per-item outcomes for bootstrap CIs. Overwritten on each run of a method.
        # Each entry carries enough information to compute every metric on its own
        # correct denominator (see src/tracemap/ai_mapping/statistics.py).
        from tracemap.ai_mapping.statistics import ItemOutcome

        self._outcomes[method.name] = [
            ItemOutcome(
                is_mappable=(r.item.expected_concept_id is not None),
                committed=(r.predicted_concept_id is not None),
                correct_prediction=(
                    r.item.expected_concept_id is not None
                    and r.predicted_concept_id == r.item.expected_concept_id
                ),
                abstained=(r.predicted_concept_id is None),
            )
            for r in results
        ]

        return EvaluationResult(
            method=method.name,
            n_total=total,
            n_mappable=n_mappable,
            n_unmappable=n_unmappable,
            top1_accuracy=(correct_top1 / n_mappable) if n_mappable else 0.0,
            precision=(len(correct) / len(committed)) if committed else 0.0,
            coverage=(len(committed) / total) if total else 0.0,
            correct_abstention_rate=(len(abstained_on_unmappable) / n_unmappable)
            if n_unmappable
            else 0.0,
        )

    def repeat(self, method: Method, repeats: int) -> dict:
        """Run `repeats` evaluations and summarise mean + stdev per metric."""
        runs = [self.run(method) for _ in range(repeats)]

        def _m(getter):
            vals = [getter(r) for r in runs]
            return {
                "mean": statistics.mean(vals),
                "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            }

        return {
            "method": method.name,
            "runs": repeats,
            "top1_accuracy": _m(lambda r: r.top1_accuracy),
            "precision": _m(lambda r: r.precision),
            "coverage": _m(lambda r: r.coverage),
            "correct_abstention_rate": _m(lambda r: r.correct_abstention_rate),
        }


def evaluate_all(
    methods: list[Method], items: list[GoldItem] | None = None, repeats: int = 5
) -> list[dict]:
    items = items or load_gold_set()
    e = Evaluation(items)
    return [e.repeat(m, repeats=repeats) for m in methods]


def outcomes_for(ev: Evaluation, method_name: str, metric: str | None = None):
    """Return per-item outcomes for a method from the last run.

    Pass `metric=None` to get ItemOutcome records (new code; used by bootstrap_all).
    Pass a metric name ('correct_top1' / 'committed' / 'correct_abstention') to get a
    bool list (compatible with the old deprecated bootstrap_diff signature).
    """
    rows = ev._outcomes.get(method_name, [])
    if metric is None:
        return rows
    attr_map = {
        "correct_top1": "correct_prediction",
        "committed": "committed",
        "correct_abstention": lambda o: (not o.is_mappable) and o.abstained,
    }
    key = attr_map.get(metric, metric)
    if callable(key):
        return [key(r) for r in rows]
    return [getattr(r, key) for r in rows]
