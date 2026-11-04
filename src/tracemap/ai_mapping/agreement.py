"""Per-item agreement across repeated LLM calls.

For each test item, call the method `n` times and record the concept_id picked each
time (or None for abstain). Report:
- items where every run agreed on the same concept_id (or every run abstained)
- items where runs split
- per-item majority vote and what fraction of runs matched it

This is what tells us whether the earlier zero-stdev at 3 decimals reflects Sonnet
being highly consistent, or something odd in the harness.
"""

from collections import Counter
from dataclasses import dataclass

from tracemap.ai_mapping.gold import GoldItem


@dataclass(frozen=True)
class AgreementRow:
    item: GoldItem
    predictions: list[int | None]  # concept_id per run (None = abstain)
    unanimous: bool
    majority_choice: int | None
    majority_count: int


def compute_agreement(method, items: list[GoldItem], runs: int) -> list[AgreementRow]:
    rows: list[AgreementRow] = []
    for item in items:
        preds: list[int | None] = []
        for _ in range(runs):
            pred = method.predict(item.term)
            preds.append(pred.concept_id)
        counter = Counter(preds)
        majority_choice, majority_count = counter.most_common(1)[0]
        rows.append(
            AgreementRow(
                item=item,
                predictions=preds,
                unanimous=(len(counter) == 1),
                majority_choice=majority_choice,
                majority_count=majority_count,
            )
        )
    return rows


def summarise(rows: list[AgreementRow], runs: int) -> dict:
    n = len(rows)
    if n == 0:
        return {"items": 0}
    unanimous = sum(1 for r in rows if r.unanimous)
    all_abstain = sum(1 for r in rows if r.unanimous and r.majority_choice is None)
    all_same_concept = sum(1 for r in rows if r.unanimous and r.majority_choice is not None)
    split = n - unanimous
    # Rows where the split makes a correctness-affecting difference.
    flip_correct = 0
    for r in rows:
        expected = r.item.expected_concept_id
        has_correct = any(p == expected for p in r.predictions)
        has_wrong_or_abstain = any(p != expected for p in r.predictions)
        if has_correct and has_wrong_or_abstain:
            flip_correct += 1
    return {
        "items": n,
        "runs": runs,
        "unanimous_items": unanimous,
        "unanimous_pct": round(100.0 * unanimous / n, 2),
        "split_items": split,
        "split_pct": round(100.0 * split / n, 2),
        "all_abstain_items": all_abstain,
        "all_same_concept_items": all_same_concept,
        "items_that_flip_correctness": flip_correct,
        "items_that_flip_correctness_pct": round(100.0 * flip_correct / n, 2),
    }
