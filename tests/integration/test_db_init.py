import pytest

from tracemap.db import connect
from tracemap.load import ddl

pytestmark = pytest.mark.integration


def test_db_init_creates_cdm_and_vocab_tables():
    with connect() as conn:
        ddl.create_schemas(conn, reset=True)
        ddl.apply_tables_and_primary_keys(conn)
        rows = conn.execute(
            "SELECT table_schema, count(*) FROM information_schema.tables "
            "WHERE table_schema IN ('cdm', 'vocab') GROUP BY table_schema"
        ).fetchall()
    counts = dict(rows)
    assert counts["vocab"] == len(ddl.VOCABULARY_TABLES)
    assert counts["cdm"] == 39 - len(ddl.VOCABULARY_TABLES)
