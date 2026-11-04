"""Safe outputs: small-number suppression and rounding, config-driven."""

from tracemap.outputs.checker import (
    OutputCheckerRules,
    check_rows,
    load_rules,
)

__all__ = ["OutputCheckerRules", "check_rows", "load_rules"]
