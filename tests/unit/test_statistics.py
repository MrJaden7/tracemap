"""Tests for the per-metric bootstrap in src/tracemap/ai_mapping/statistics.py.

The earlier version averaged a boolean over the full item list regardless of metric,
which pulled the top-1 and abstention CIs onto the wrong denominator. These tests pin
the correct behaviour down."""

from tracemap.ai_mapping.statistics import (
    ItemOutcome,
    abstention_metric,
    bootstrap_all,
    coverage_metric,
    precision_metric,
    top1_metric,
)


def _make(is_mappable: bool, committed: bool, correct: bool):
    return ItemOutcome(
        is_mappable=is_mappable,
        committed=committed,
        correct_prediction=correct,
        abstained=not committed,
    )


def test_top1_is_over_mappable_items_only():
    items = (
        [_make(True, True, True)] * 3
        + [_make(True, True, False)] * 1
        + [_make(False, True, False)] * 2  # unmappable, committed, wrong
    )
    assert top1_metric(items, items) == 3 / 4


def test_abstention_is_over_unmappable_items_only():
    items = (
        [_make(True, True, True)] * 10  # mappable, committed - irrelevant
        + [_make(False, False, False)] * 3  # unmappable, abstained - correct abstain
        + [_make(False, True, False)] * 1  # unmappable, committed - wrong, not abstained
    )
    assert abstention_metric(items, items) == 3 / 4


def test_coverage_is_over_all_items():
    items = [_make(True, True, True)] * 7 + [_make(True, False, False)] * 3
    assert coverage_metric(items, items) == 7 / 10


def test_precision_is_over_committed_items():
    items = (
        [_make(True, True, True)] * 4
        + [_make(True, True, False)] * 1
        + [_make(True, False, False)] * 5
    )
    assert precision_metric(items, items) == 4 / 5


def test_bootstrap_matches_point_estimates():
    """The mean_diff reported by bootstrap_all must equal the point-estimate diff
    computed on the full input, not the resample averages."""
    llm = [_make(True, True, True)] * 130 + [_make(True, True, False)] * 16  # 146 mappable
    llm += [_make(False, False, False)] * 24 + [_make(False, True, False)] * 5  # 29 unmappable
    hyb = [_make(True, True, True)] * 122 + [_make(True, True, False)] * 24  # 146 mappable
    hyb += [_make(False, False, False)] * 1 + [_make(False, True, False)] * 28

    ci = bootstrap_all(llm, hyb)
    # Top-1: (130-122)/146 = +0.055
    assert ci["top-1 accuracy"].mean_diff == (130 - 122) / 146
    # Correct abstention: (24-1)/29 = +0.793
    assert ci["correct abstention"].mean_diff == (24 - 1) / 29
    # Denominators are correct
    assert ci["top-1 accuracy"].n == 146
    assert ci["correct abstention"].n == 29
    assert ci["coverage"].n == 175


def test_bootstrap_returns_ci_bracketing_point_estimate_on_realistic_sample():
    llm = [_make(True, True, True)] * 130 + [_make(True, True, False)] * 16
    llm += [_make(False, False, False)] * 24 + [_make(False, True, False)] * 5
    hyb = [_make(True, True, True)] * 122 + [_make(True, True, False)] * 24
    hyb += [_make(False, False, False)] * 1 + [_make(False, True, False)] * 28

    ci = bootstrap_all(llm, hyb, n_resamples=500)
    for metric_name, c in ci.items():
        assert c.lower <= c.mean_diff <= c.upper, f"{metric_name}: CI does not bracket mean diff"
