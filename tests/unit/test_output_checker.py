from tracemap.outputs.checker import OutputCheckerRules, check_rows


def test_counts_below_threshold_are_suppressed():
    rules = OutputCheckerRules(suppression_threshold=10, rounding_base=5)
    out = check_rows([{"n_patients": 7, "sex": "M"}], rules)
    assert out[0]["n_patients"] == "<10"


def test_surviving_counts_are_rounded_to_nearest_base():
    rules = OutputCheckerRules(suppression_threshold=10, rounding_base=5)
    out = check_rows([{"n_patients": 23}], rules)
    assert out[0]["n_patients"] == 25
    out = check_rows([{"n_patients": 22}], rules)
    assert out[0]["n_patients"] == 20


def test_dependent_fields_suppressed_when_row_has_suppression():
    rules = OutputCheckerRules()
    out = check_rows([{"n_patients": 3, "survival_rate": 0.85}], rules)
    assert out[0]["n_patients"] == "<10"
    assert out[0]["survival_rate"] == "<10"


def test_non_count_fields_pass_through():
    rules = OutputCheckerRules()
    out = check_rows([{"n_patients": 15, "diagnosis_year": 2020, "sex": "M"}], rules)
    assert out[0]["sex"] == "M"
    assert out[0]["diagnosis_year"] == 2020


def test_null_counts_left_unchanged():
    rules = OutputCheckerRules()
    out = check_rows([{"n_patients": None}], rules)
    assert out[0]["n_patients"] is None
