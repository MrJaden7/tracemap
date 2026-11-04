"""Bootstrap confidence intervals for AI mapping metrics.

Pairs items by index across the two methods so the bootstrap samples the same items for
both methods on each resample. This is the right thing to do here: we care about the
difference on each item, not two independent distributions.
"""

import random
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class CIResult:
    mean_diff: float
    lower: float
    upper: float
    n: int


def _per_item_pairs(a_outcomes: list[bool], b_outcomes: list[bool]) -> list[int]:
    """1 where a is correct and b is not, -1 where b is correct and a is not, 0 otherwise."""
    if len(a_outcomes) != len(b_outcomes):
        raise ValueError("outcome lists must have the same length")
    return [int(a) - int(b) for a, b in zip(a_outcomes, b_outcomes, strict=True)]


def bootstrap_diff(
    a_outcomes: list[bool],
    b_outcomes: list[bool],
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> CIResult:
    """95% paired-bootstrap confidence interval for (mean(a) - mean(b))."""
    pairs = _per_item_pairs(a_outcomes, b_outcomes)
    n = len(pairs)
    if n == 0:
        return CIResult(0.0, 0.0, 0.0, 0)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_resamples):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        diffs.append(sum(sample) / n)
    diffs.sort()
    tail = (1.0 - confidence) / 2.0
    lower = diffs[int(tail * n_resamples)]
    upper = diffs[int((1.0 - tail) * n_resamples) - 1]
    mean_diff = statistics.mean(pairs)
    return CIResult(mean_diff=mean_diff, lower=lower, upper=upper, n=n)
