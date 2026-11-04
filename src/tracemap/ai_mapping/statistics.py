"""Bootstrap confidence intervals for AI mapping metrics.

Each metric has its own denominator, so each bootstrap resamples from the appropriate
pool of items:

- top-1 accuracy    : resample over MAPPABLE items (n = count of mappable). Outcome is
                      "method's predicted concept_id equals the expected one".
- correct abstention: resample over UNMAPPABLE items. Outcome is "method predicted None".
- coverage          : resample over ALL items. Outcome is "method committed".
- precision         : resample over ALL items; on each sample compute correct/committed
                      separately for each method; diff = prec_A - prec_B. Resamples where
                      either method committed to nothing are skipped so the ratio is
                      defined for both.

The earlier implementation used a single boolean over the full set for every metric,
which pulled every CI denominator down to the full-set size and made the top-1 and
abstention CIs numerically incorrect. This file replaces that approach.
"""

import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CIResult:
    mean_diff: float
    lower: float
    upper: float
    n: int
    note: str = ""


@dataclass(frozen=True)
class ItemOutcome:
    """Per-item outcome row. One per test item, one list per method."""

    is_mappable: bool  # from the gold set
    committed: bool  # method produced a non-None concept_id (safety-gated)
    correct_prediction: bool  # method's prediction equals the expected concept_id
    abstained: bool  # method predicted None


def _tails(sorted_values: list[float], confidence: float) -> tuple[float, float]:
    n = len(sorted_values)
    tail = (1.0 - confidence) / 2.0
    lo_idx = max(0, int(tail * n))
    hi_idx = min(n - 1, int((1.0 - tail) * n) - 1)
    return sorted_values[lo_idx], sorted_values[hi_idx]


def bootstrap_metric_diff(
    a_outcomes: list[ItemOutcome],
    b_outcomes: list[ItemOutcome],
    metric: Callable[[list[ItemOutcome], list[ItemOutcome]], float | None],
    item_filter: Callable[[ItemOutcome], bool],
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> CIResult:
    """Paired bootstrap for (metric(a) - metric(b)) over items matching `item_filter`.

    Pairs items by index (same resample indices applied to both methods), which is the
    right thing to do because both methods see the same items.
    """
    if len(a_outcomes) != len(b_outcomes):
        raise ValueError("outcome lists must have the same length")
    idxs = [i for i, o in enumerate(a_outcomes) if item_filter(o)]
    n = len(idxs)
    if n == 0:
        return CIResult(0.0, 0.0, 0.0, 0, "no items match the filter")

    rng = random.Random(seed)
    diffs: list[float] = []
    skipped = 0
    for _ in range(n_resamples):
        sample_idx = [idxs[rng.randrange(n)] for _ in range(n)]
        a_sample = [a_outcomes[i] for i in sample_idx]
        b_sample = [b_outcomes[i] for i in sample_idx]
        a_metric = metric(a_sample, a_sample)
        b_metric = metric(b_sample, b_sample)
        if a_metric is None or b_metric is None:
            skipped += 1
            continue
        diffs.append(a_metric - b_metric)
    if not diffs:
        return CIResult(0.0, 0.0, 0.0, n, "all resamples skipped")
    diffs.sort()
    lower, upper = _tails(diffs, confidence)
    full_a = metric(a_outcomes, a_outcomes)
    full_b = metric(b_outcomes, b_outcomes)
    mean_diff = (full_a or 0.0) - (full_b or 0.0)
    note = f"{skipped} of {n_resamples} resamples skipped" if skipped else ""
    return CIResult(mean_diff=mean_diff, lower=lower, upper=upper, n=n, note=note)


# Metric definitions. All take two identical lists (the paired bootstrap passes the same
# sample twice) so the signature is uniform across metrics, even though top-1 /
# coverage / abstention only need one argument.


def top1_metric(sample: list[ItemOutcome], _unused: list[ItemOutcome]) -> float | None:
    mappable = [o for o in sample if o.is_mappable]
    if not mappable:
        return None
    correct = sum(1 for o in mappable if o.correct_prediction)
    return correct / len(mappable)


def coverage_metric(sample: list[ItemOutcome], _unused: list[ItemOutcome]) -> float | None:
    if not sample:
        return None
    return sum(1 for o in sample if o.committed) / len(sample)


def abstention_metric(sample: list[ItemOutcome], _unused: list[ItemOutcome]) -> float | None:
    unmappable = [o for o in sample if not o.is_mappable]
    if not unmappable:
        return None
    return sum(1 for o in unmappable if o.abstained) / len(unmappable)


def precision_metric(sample: list[ItemOutcome], _unused: list[ItemOutcome]) -> float | None:
    committed = [o for o in sample if o.committed]
    if not committed:
        return None
    return sum(1 for o in committed if o.correct_prediction) / len(committed)


def bootstrap_all(
    a: list[ItemOutcome], b: list[ItemOutcome], n_resamples: int = 2000
) -> dict[str, CIResult]:
    """Compute all four CIs on their correct denominators."""
    return {
        "top-1 accuracy": bootstrap_metric_diff(
            a, b, top1_metric, lambda o: o.is_mappable, n_resamples
        ),
        "precision": bootstrap_metric_diff(a, b, precision_metric, lambda o: True, n_resamples),
        "coverage": bootstrap_metric_diff(a, b, coverage_metric, lambda o: True, n_resamples),
        "correct abstention": bootstrap_metric_diff(
            a, b, abstention_metric, lambda o: not o.is_mappable, n_resamples
        ),
    }


# Backwards-compatible alias so callers that used the old name still work. New code
# should use bootstrap_metric_diff with an explicit metric + filter.
def bootstrap_diff(
    a_outcomes: list[bool],
    b_outcomes: list[bool],
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> CIResult:
    """[DEPRECATED] Old API that averaged bool outcomes over the full item list. Kept so
    old tests still import. Returns the CI of mean(a) - mean(b) over len(a) items."""
    if len(a_outcomes) != len(b_outcomes):
        raise ValueError("outcome lists must have the same length")
    pairs = [int(x) - int(y) for x, y in zip(a_outcomes, b_outcomes, strict=True)]
    n = len(pairs)
    if n == 0:
        return CIResult(0.0, 0.0, 0.0, 0)
    rng = random.Random(seed)
    diffs = [sum(pairs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_resamples)]
    diffs.sort()
    lower, upper = _tails(diffs, confidence)
    return CIResult(mean_diff=statistics.mean(pairs), lower=lower, upper=upper, n=n)
