"""Output checker: the Five Safes 'safe outputs' step.

Every cohort query result goes through `check_rows` before export. The rules are loaded
from `config/output_rules.yml` so another environment (or the TVS SDE's own policy)
can plug in its own thresholds without editing the queries.

Rules in the default config:
- Count-shaped fields (names ending in '_count' or 'count', 'n', 'patients', 'rows')
  below the suppression threshold (10 by default) are replaced with '<10'.
- Surviving counts are rounded to the nearest multiple of `rounding_base` (5 by default).
- Any field whose name ends in '_pct', '_percent', '_rate', '_share' or is literally
  'percent' is suppressed when any other field in the same row has been suppressed.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

COUNT_SUFFIXES = ("_count", "count", "_n", "patients", "rows", "n_patients")
DEPENDENT_SUFFIXES = ("_pct", "_percent", "percent", "_rate", "_share", "pct")


@dataclass(frozen=True)
class OutputCheckerRules:
    suppression_threshold: int = 10
    rounding_base: int = 5
    suppress_dependent_fields: bool = True
    suppressed_label: str = "<10"


def load_rules(path: Path | None = None) -> OutputCheckerRules:
    if path is None:
        from tracemap.config import REPO_ROOT

        path = REPO_ROOT / "config" / "output_rules.yml"
    if not path.is_file():
        return OutputCheckerRules()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return OutputCheckerRules(
        suppression_threshold=int(data.get("suppression_threshold", 10)),
        rounding_base=int(data.get("rounding_base", 5)),
        suppress_dependent_fields=bool(data.get("suppress_dependent_fields", True)),
        suppressed_label=str(data.get("suppressed_label", "<10")),
    )


def _is_count_field(name: str) -> bool:
    return any(name.lower().endswith(s) for s in COUNT_SUFFIXES)


def _is_dependent_field(name: str) -> bool:
    return any(name.lower().endswith(s) for s in DEPENDENT_SUFFIXES)


def _round_to(value: int, base: int) -> int:
    if base <= 1:
        return value
    return int(base * round(value / base))


def check_row(row: dict[str, Any], rules: OutputCheckerRules) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    suppressed_any = False
    for name, value in row.items():
        if not _is_count_field(name):
            continue
        if value is None or isinstance(value, str):
            continue
        try:
            n = int(value)
        except (TypeError, ValueError):
            continue
        if n < rules.suppression_threshold:
            out[name] = rules.suppressed_label
            suppressed_any = True
        else:
            out[name] = _round_to(n, rules.rounding_base)
    if suppressed_any and rules.suppress_dependent_fields:
        for name in row:
            if _is_dependent_field(name):
                out[name] = rules.suppressed_label
    # Also round float fields that look like they summarise a suppressed row.
    if suppressed_any:
        for name, value in list(row.items()):
            if _is_dependent_field(name) and isinstance(value, float):
                out[name] = rules.suppressed_label
    return out


def check_rows(
    rows: list[dict[str, Any]], rules: OutputCheckerRules | None = None
) -> list[dict[str, Any]]:
    rules = rules or load_rules()
    return [check_row(r, rules) for r in rows]
