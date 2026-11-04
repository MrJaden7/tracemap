from tracemap.load import ddl


def test_vocabulary_tables_route_to_vocab_schema():
    stmt = "CREATE TABLE @cdmDatabaseSchema.CONCEPT (concept_id integer NOT NULL)"
    assert ddl.route_statement(stmt).startswith("CREATE TABLE vocab.concept ")


def test_clinical_tables_route_to_cdm_schema():
    stmt = "CREATE TABLE @cdmDatabaseSchema.person (person_id integer NOT NULL)"
    assert ddl.route_statement(stmt).startswith("CREATE TABLE cdm.person ")


def test_foreign_key_crosses_schemas():
    stmt = (
        "ALTER TABLE @cdmDatabaseSchema.person ADD CONSTRAINT fk FOREIGN KEY (gender_concept_id) "
        "REFERENCES @cdmDatabaseSchema.CONCEPT (CONCEPT_ID)"
    )
    routed = ddl.route_statement(stmt)
    assert "ALTER TABLE cdm.person" in routed
    assert "REFERENCES vocab.concept" in routed


def test_official_ddl_has_no_unrouted_placeholders():
    for path in (ddl.DDL_FILE, ddl.PRIMARY_KEYS_FILE, ddl.INDICES_FILE):
        for stmt in ddl.routed_statements(path):
            assert "@cdmDatabaseSchema" not in stmt, path.name


def test_official_ddl_defines_all_phase1_tables():
    created = {
        stmt.split()[2]
        for stmt in ddl.routed_statements(ddl.DDL_FILE)
        if stmt.upper().startswith("CREATE TABLE")
    }
    phase1 = {
        "person",
        "observation_period",
        "visit_occurrence",
        "condition_occurrence",
        "drug_exposure",
        "measurement",
        "procedure_occurrence",
        "observation",
        "death",
        "location",
        "care_site",
        "provider",
        "cdm_source",
        "metadata",
    }
    assert {f"cdm.{t}" for t in phase1} <= created
    assert "vocab.concept" in created
