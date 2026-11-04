"""Make every cdm.* table conform to the full OHDSI CDM v5.4 DDL column set.

TraceMap's dbt models use `materialized: table`, which replaces the table with only the
columns the mapping spec declares. The OHDSI DDL defines more columns per table (many
optional, nullable). Downstream tools like the OHDSI Data Quality Dashboard need those
columns to exist (even if empty) so their field-level checks can run.

This script reads the authoritative DDL in `ddl/OMOPCDM_postgresql_5.4_ddl.sql`, enumerates
the expected columns per table, compares with the current cdm.* schema, and runs
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS <col> <type> NULL` for every missing column.

Idempotent: running it twice has no effect the second time.
"""

import re

from tracemap.db import connect
from tracemap.load import ddl

_COL_RE = re.compile(r"^\s*([a-z_][a-z_0-9]*)\s+([^\s,]+(?:\([^)]*\))?)", re.IGNORECASE)


def parse_ddl_columns() -> dict[str, list[tuple[str, str]]]:
    """Return {table_name: [(column_name, type_sql), ...]} from the OHDSI DDL."""
    text = ddl.DDL_FILE.read_text(encoding="utf-8")
    tables: dict[str, list[tuple[str, str]]] = {}
    for match in re.finditer(
        r"CREATE TABLE @cdmDatabaseSchema\.([a-z_]+)\s*\((.*?)\);",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        table = match.group(1).lower()
        body = match.group(2)
        cols: list[tuple[str, str]] = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            m = _COL_RE.match(line)
            if m is None:
                continue
            col, col_type = m.group(1).lower(), m.group(2)
            cols.append((col, col_type))
        tables[table] = cols
    return tables


def current_columns(conn, schema: str, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT lower(column_name) FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    ).fetchall()
    return {r[0] for r in rows}


def conform_schema(schema: str = "cdm") -> dict[str, list[str]]:
    """ALTER cdm.<table> ADD COLUMN missing columns NULL. Returns per-table added columns."""
    expected = parse_ddl_columns()
    added: dict[str, list[str]] = {}
    with connect() as conn:
        for table, cols in expected.items():
            if ddl.schema_for_table(table) != schema:
                continue
            existing = current_columns(conn, schema, table)
            if not existing:
                continue  # table does not exist in this schema
            missing = [(c, t) for c, t in cols if c not in existing]
            if not missing:
                continue
            for col, col_type in missing:
                conn.execute(
                    f'ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS "{col}" {col_type} NULL'
                )
            added[table] = [c for c, _ in missing]
        conn.commit()
    return added
