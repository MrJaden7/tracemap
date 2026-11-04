"""Integration test for db init. Runs against the isolated tracemap_test database
so it cannot destroy the developer's loaded vocabulary."""

import pytest

from tracemap.load import ddl

pytestmark = pytest.mark.integration


def test_db_init_creates_cdm_and_vocab_tables(test_db_conn):
    ddl.create_schemas(test_db_conn, reset=True)
    ddl.apply_tables_and_primary_keys(test_db_conn)
    rows = test_db_conn.execute(
        "SELECT table_schema, count(*) FROM information_schema.tables "
        "WHERE table_schema IN ('cdm', 'vocab') GROUP BY table_schema"
    ).fetchall()
    counts = dict(rows)
    assert counts["vocab"] == len(ddl.VOCABULARY_TABLES)
    assert counts["cdm"] == 39 - len(ddl.VOCABULARY_TABLES)
