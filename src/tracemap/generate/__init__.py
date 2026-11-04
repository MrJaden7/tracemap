"""Generator: reads mapping_spec/ YAML and produces dbt SQL models, dbt tests, mapping
documentation and Mermaid lineage diagrams. Nothing hand-written downstream can drift
from the spec, because everything is overwritten on each `tracemap generate`."""

from tracemap.generate.sql import generate_cdm_model, write_cdm_models
from tracemap.generate.tests import write_schema_tests

__all__ = ["generate_cdm_model", "write_cdm_models", "write_schema_tests"]
