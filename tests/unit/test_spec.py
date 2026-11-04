from pathlib import Path

import pytest
from pydantic import ValidationError

from tracemap.spec import load_all_specs, load_spec
from tracemap.spec.models import (
    CopyRule,
    LookupRule,
    MappingSpec,
    StandardConceptMapRule,
)


def test_person_spec_loads(tmp_path: Path) -> None:
    spec = load_spec(Path("mapping_spec/person.yml"))
    assert spec.target_table == "person"
    assert spec.source_systems == ["synthea"]
    source = spec.sources[0]
    assert source.source_table == "raw.synthea_patients"
    rules_by_target = {r.target: r for r in source.fields}
    assert isinstance(rules_by_target["person_id"], LookupRule)
    assert isinstance(rules_by_target["gender_concept_id"], StandardConceptMapRule)
    assert isinstance(rules_by_target["person_source_value"], CopyRule)


def test_load_all_specs_returns_every_target_table():
    specs = load_all_specs()
    assert "person" in specs
    assert all(isinstance(v, MappingSpec) for v in specs.values())


def test_unknown_rule_fails_validation(tmp_path: Path) -> None:
    yml = tmp_path / "x.yml"
    yml.write_text(
        "target_table: person\nspec_version: 0.1.0\n"
        "sources:\n  - source_system: s\n    source_table: raw.x\n    grain: g\n"
        "    fields:\n      - target: id\n        rule: bogus_rule\n        from: id\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_spec(yml)


def test_duplicate_target_rejected(tmp_path: Path) -> None:
    yml = tmp_path / "x.yml"
    yml.write_text(
        "target_table: person\nspec_version: 0.1.0\n"
        "sources:\n  - source_system: s\n    source_table: raw.x\n    grain: g\n"
        "    fields:\n"
        "      - target: id\n        rule: copy\n        from: a\n"
        "      - target: id\n        rule: copy\n        from: b\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="Duplicate target field"):
        load_spec(yml)


def test_unknown_key_in_spec_rejected(tmp_path: Path) -> None:
    yml = tmp_path / "x.yml"
    yml.write_text(
        "target_table: person\nspec_version: 0.1.0\nbogus_key: 1\n"
        "sources:\n  - source_system: s\n    source_table: raw.x\n    grain: g\n"
        "    fields:\n      - target: id\n        rule: copy\n        from: id\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_spec(yml)
