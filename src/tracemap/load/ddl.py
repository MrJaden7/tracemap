"""Create TraceMap schemas and apply the official OHDSI CDM v5.4 PostgreSQL DDL.

The DDL files in ddl/ are copied unchanged from OHDSI/CommonDataModel. They use a single
@cdmDatabaseSchema placeholder for every table. TraceMap keeps vocabulary tables in their
own `vocab` schema (see docs/decisions), so each statement is routed by table name:
vocabulary tables go to `vocab`, everything else goes to `cdm`.
"""

import re
from pathlib import Path

import psycopg

from tracemap.config import REPO_ROOT

DDL_DIR = REPO_ROOT / "ddl"
DDL_FILE = DDL_DIR / "OMOPCDM_postgresql_5.4_ddl.sql"
PRIMARY_KEYS_FILE = DDL_DIR / "OMOPCDM_postgresql_5.4_primary_keys.sql"
INDICES_FILE = DDL_DIR / "OMOPCDM_postgresql_5.4_indices.sql"
ETL_META_FILE = DDL_DIR / "tracemap_etl_meta.sql"

PROJECT_SCHEMAS = ("raw", "vocab", "cdm", "etl_meta")

VOCABULARY_TABLES = frozenset(
    {
        "concept",
        "vocabulary",
        "domain",
        "concept_class",
        "concept_relationship",
        "relationship",
        "concept_synonym",
        "concept_ancestor",
        "source_to_concept_map",
        "drug_strength",
    }
)

_TABLE_REF = re.compile(r"@cdmDatabaseSchema\.(\w+)", re.IGNORECASE)


def schema_for_table(table: str) -> str:
    return "vocab" if table.lower() in VOCABULARY_TABLES else "cdm"


def split_statements(sql: str) -> list[str]:
    """Split an OHDSI DDL file into statements, dropping comment-only lines."""
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def route_statement(statement: str) -> str:
    """Replace every @cdmDatabaseSchema.<table> with the schema that table belongs in."""
    return _TABLE_REF.sub(
        lambda m: f"{schema_for_table(m.group(1))}.{m.group(1).lower()}", statement
    )


def routed_statements(path: Path) -> list[str]:
    return [route_statement(s) for s in split_statements(path.read_text(encoding="utf-8"))]


def cdm_tables_exist(conn: psycopg.Connection) -> bool:
    row = conn.execute("SELECT to_regclass('cdm.person') IS NOT NULL").fetchone()
    return bool(row and row[0])


def create_schemas(conn: psycopg.Connection, reset: bool = False) -> None:
    for schema in PROJECT_SCHEMAS:
        if reset:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def apply_tables_and_primary_keys(conn: psycopg.Connection) -> int:
    statements = (
        routed_statements(DDL_FILE)
        + routed_statements(PRIMARY_KEYS_FILE)
        + split_statements(ETL_META_FILE.read_text(encoding="utf-8"))
    )
    for statement in statements:
        conn.execute(statement)
    return len(statements)


def target_schema(statement: str) -> str:
    """The schema of the first table an OHDSI statement refers to."""
    match = _TABLE_REF.search(statement)
    if match is None:
        raise ValueError(f"No @cdmDatabaseSchema table in statement: {statement[:80]}")
    return schema_for_table(match.group(1))


def index_statements(schema: str, include_cluster: bool = False) -> list[str]:
    """OHDSI index statements for one schema.

    CLUSTER physically reorders a table on disk. It does not change query results and
    takes a long time on the multi-gigabyte vocabulary tables, so it is off by default.
    """
    selected = []
    for statement in split_statements(INDICES_FILE.read_text(encoding="utf-8")):
        if target_schema(statement) != schema:
            continue
        if statement.upper().startswith("CLUSTER") and not include_cluster:
            continue
        selected.append(route_statement(statement))
    return selected


def apply_indices(conn: psycopg.Connection, schema: str, include_cluster: bool = False) -> int:
    """Apply OHDSI indices for one schema. Run after bulk loading, since indexes slow inserts."""
    statements = index_statements(schema, include_cluster)
    for statement in statements:
        conn.execute(statement)
    return len(statements)
