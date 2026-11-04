"""Mapping specification. Mappings are declared once in mapping_spec/ YAML files and every
other artefact (dbt SQL, dbt tests, docs, lineage diagrams) is generated from them."""

from tracemap.spec.models import (
    FieldRule,
    MappingSpec,
    SourceMapping,
    load_all_specs,
    load_spec,
)

__all__ = ["FieldRule", "MappingSpec", "SourceMapping", "load_all_specs", "load_spec"]
