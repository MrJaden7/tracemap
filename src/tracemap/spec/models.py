"""Pydantic models for mapping specification YAML.

A spec file describes how one target OMOP CDM table is built, by naming one or more
source tables and declaring, field by field, the rule that produces each target column.
Every rule is explicit. Unknown rules are rejected at load time, so a typo in a YAML file
fails the build instead of producing silently-wrong data.
"""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tracemap.config import REPO_ROOT

MAPPING_SPEC_DIR = REPO_ROOT / "mapping_spec"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------------------
# Field rules. Each is a discriminated union member tagged by `rule`.
# --------------------------------------------------------------------------------------


class CopyRule(_StrictModel):
    """Copy the source column into the target column verbatim (as text)."""

    rule: Literal["copy"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    notes: str | None = None


class CastDateRule(_StrictModel):
    """Parse the source value as a date (YYYY-MM-DD or ISO 8601) and store as DATE."""

    rule: Literal["cast_date"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    notes: str | None = None


class CastDateTimeRule(_StrictModel):
    """Parse the source value as a timestamp and store as TIMESTAMP."""

    rule: Literal["cast_datetime"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    notes: str | None = None


class CastIntRule(_StrictModel):
    """Parse the source value as an integer."""

    rule: Literal["cast_int"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    notes: str | None = None


class CastNumericRule(_StrictModel):
    """Parse the source value as a number."""

    rule: Literal["cast_numeric"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    notes: str | None = None


class ConstantRule(_StrictModel):
    """Set the target column to a constant value."""

    rule: Literal["constant"]
    target: str
    value: str | int | float | None
    label: str | None = None
    notes: str | None = None


class LookupRule(_StrictModel):
    """Look the source value up in a mapping table, write the result into the target."""

    rule: Literal["lookup"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    via: str  # table name, e.g. etl_meta.person_key_map
    notes: str | None = None


class SourceConceptLookupRule(_StrictModel):
    """Find concept_id for a source code in the given source vocabulary."""

    rule: Literal["source_concept_lookup"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    source_vocabulary: str
    preprocess: str | None = None
    notes: str | None = None


class StandardConceptMapRule(_StrictModel):
    """Map a source code to its standard concept via concept_relationship.

    If no mapping exists, `on_unmapped` decides whether to emit 0 or null.
    When `domain_routing` is true, the generator uses the domain of the mapped standard
    concept to route the row into the correct destination table.
    """

    rule: Literal["standard_concept_map"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    source_vocabulary: str
    relationship: str = "Maps to"
    on_unmapped: Literal["concept_id_0", "null"] = "concept_id_0"
    preprocess: str | None = None
    domain_routing: bool = False
    notes: str | None = None


class UnitMapRule(_StrictModel):
    """Map a source unit string to a UCUM standard concept."""

    rule: Literal["unit_map"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    on_unmapped: Literal["concept_id_0", "null"] = "concept_id_0"
    notes: str | None = None


class ValueAsConceptMapRule(_StrictModel):
    """Map a non-numeric result value to a standard concept."""

    rule: Literal["value_as_concept_map"]
    target: str
    from_: Annotated[str, Field(alias="from")]
    source_vocabulary: str = "SNOMED"
    on_unmapped: Literal["concept_id_0", "null"] = "concept_id_0"
    notes: str | None = None


FieldRule = Annotated[
    CopyRule
    | CastDateRule
    | CastDateTimeRule
    | CastIntRule
    | CastNumericRule
    | ConstantRule
    | LookupRule
    | SourceConceptLookupRule
    | StandardConceptMapRule
    | UnitMapRule
    | ValueAsConceptMapRule,
    Field(discriminator="rule"),
]


# --------------------------------------------------------------------------------------
# Spec top-level shapes
# --------------------------------------------------------------------------------------


class SourceMapping(_StrictModel):
    source_system: str
    source_table: str
    grain: str
    where: str | None = None
    fields: list[FieldRule]

    @field_validator("fields")
    @classmethod
    def unique_targets(cls, fields: list[FieldRule]) -> list[FieldRule]:
        seen = set()
        for rule in fields:
            if rule.target in seen:
                raise ValueError(f"Duplicate target field: {rule.target}")
            seen.add(rule.target)
        return fields


class MappingSpec(_StrictModel):
    target_table: str
    spec_version: str
    description: str | None = None
    sources: list[SourceMapping]

    @property
    def source_systems(self) -> list[str]:
        return sorted({s.source_system for s in self.sources})


# --------------------------------------------------------------------------------------
# Loader
# --------------------------------------------------------------------------------------


def load_spec(path: Path) -> MappingSpec:
    """Parse and validate one YAML spec."""
    return MappingSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_all_specs(spec_dir: Path | None = None) -> dict[str, MappingSpec]:
    """Parse and validate every YAML spec in `mapping_spec/`."""
    spec_dir = spec_dir or MAPPING_SPEC_DIR
    specs: dict[str, MappingSpec] = {}
    for path in sorted(spec_dir.glob("*.yml")):
        spec = load_spec(path)
        if spec.target_table in specs:
            raise ValueError(f"Duplicate target_table across specs: {spec.target_table}")
        specs[spec.target_table] = spec
    return specs
