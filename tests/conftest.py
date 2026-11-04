"""Shared pytest fixtures.

Integration tests that mutate the database connect to a separate `tracemap_test` database
so they can drop and recreate schemas without destroying the developer's loaded vocabulary.
Create it once with:

    docker exec tracemap-postgres psql -U tracemap -d postgres -c \\
        "CREATE DATABASE tracemap_test WITH OWNER tracemap"
"""

import psycopg
import pytest

from tracemap.config import get_settings


@pytest.fixture
def test_db_conn():
    """A connection to the isolated tracemap_test database."""
    settings = get_settings()
    conninfo = (
        f"host={settings.db_host} port={settings.db_port} dbname=tracemap_test "
        f"user={settings.db_user} password={settings.db_password}"
    )
    with psycopg.connect(conninfo) as conn:
        yield conn
