from tracemap.lineage.trace import TRACES, TraceSpec


def test_every_trace_spec_has_coherent_shape():
    for name, spec in TRACES.items():
        assert spec.cdm_table == name
        if spec.shape == "key_map":
            assert spec.key_map_table is not None
            assert spec.key_map_id_column is not None
        else:
            assert spec.key_map_table is None
            assert spec.key_map_id_column is None


def test_source_tables_are_raw_schema():
    for spec in TRACES.values():
        assert spec.source_table.startswith("raw.")


def test_all_specs_are_frozen_dataclasses():
    # Protects against trace specs being mutated at runtime.
    for spec in TRACES.values():
        assert isinstance(spec, TraceSpec)
