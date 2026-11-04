"""Mapping coverage: percentage of rows (and distinct codes) mapped to a standard
concept per source system and domain, with the top unmapped codes by frequency.

Written to etl_meta.mapping_coverage on every run so the README and docs can show it.
"""

from dataclasses import dataclass

import psycopg

COVERAGE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS etl_meta.mapping_coverage (
    run_id              bigint      NOT NULL,
    source_system       text        NOT NULL,
    domain              text        NOT NULL,
    total_rows          bigint      NOT NULL,
    mapped_rows         bigint      NOT NULL,
    row_coverage_pct    numeric(5,2) NOT NULL,
    distinct_codes      bigint      NOT NULL,
    mapped_codes        bigint      NOT NULL,
    code_coverage_pct   numeric(5,2) NOT NULL,
    recorded_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, source_system, domain)
)
"""

UNMAPPED_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS etl_meta.unmapped_codes (
    run_id              bigint      NOT NULL,
    source_system       text        NOT NULL,
    domain              text        NOT NULL,
    source_code         text        NOT NULL,
    row_count           bigint      NOT NULL,
    recorded_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, source_system, domain, source_code)
)
"""

# (cdm_table, source_code_column, standard_concept_column)
DOMAINS = [
    ("condition_occurrence", "condition_source_value", "condition_concept_id"),
    ("drug_exposure", "drug_source_value", "drug_concept_id"),
    ("procedure_occurrence", "procedure_source_value", "procedure_concept_id"),
    ("measurement", "measurement_source_value", "measurement_concept_id"),
    ("observation", "observation_source_value", "observation_concept_id"),
    ("visit_occurrence", "visit_source_value", "visit_concept_id"),
]


@dataclass(frozen=True)
class CoverageRow:
    source_system: str
    domain: str
    total_rows: int
    mapped_rows: int
    row_coverage_pct: float
    distinct_codes: int
    mapped_codes: int
    code_coverage_pct: float


def _latest_run(conn: psycopg.Connection) -> int | None:
    row = conn.execute(
        "SELECT run_id FROM etl_meta.cdm_run "
        "WHERE status = 'completed' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def compute_coverage(conn: psycopg.Connection) -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    for table, src_col, std_col in DOMAINS:
        q = (
            f"SELECT count(*) AS total_rows, "
            f"       sum(({std_col} > 0)::int) AS mapped_rows, "
            f"       count(distinct {src_col}) AS distinct_codes, "
            f"       count(distinct case when {std_col} > 0 then {src_col} end) AS mapped_codes "
            f"FROM cdm.{table}"
        )
        r = conn.execute(q).fetchone()
        if r is None:
            continue
        total, mapped, distinct, mapped_distinct = (int(v or 0) for v in r)
        row_pct = round(100.0 * mapped / total, 2) if total else 0.0
        code_pct = round(100.0 * mapped_distinct / distinct, 2) if distinct else 0.0
        rows.append(
            CoverageRow(
                "synthea", table, total, mapped, row_pct, distinct, mapped_distinct, code_pct
            )
        )
    return rows


def top_unmapped(conn: psycopg.Connection, limit: int = 20) -> list[tuple[str, str, int]]:
    """Return (domain, source_code, row_count) for the 20 most frequent unmapped codes
    across every domain, used for the README and the docs."""
    out = []
    for table, src_col, std_col in DOMAINS:
        rows = conn.execute(
            f"SELECT {src_col} AS code, count(*) AS n "
            f"FROM cdm.{table} WHERE {std_col} = 0 AND {src_col} IS NOT NULL "
            f"GROUP BY {src_col} ORDER BY n DESC LIMIT %s",
            (limit,),
        ).fetchall()
        for code, n in rows:
            out.append((table, code, int(n)))
    return sorted(out, key=lambda x: -x[2])[:limit]


def write_coverage_table(conn: psycopg.Connection) -> int:
    conn.execute(COVERAGE_TABLE_DDL)
    conn.execute(UNMAPPED_TABLE_DDL)
    run_id = _latest_run(conn)
    if run_id is None:
        return 0
    rows = compute_coverage(conn)
    conn.execute("DELETE FROM etl_meta.mapping_coverage WHERE run_id = %s", (run_id,))
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO etl_meta.mapping_coverage "
            "(run_id, source_system, domain, total_rows, mapped_rows, row_coverage_pct, "
            " distinct_codes, mapped_codes, code_coverage_pct) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    run_id,
                    r.source_system,
                    r.domain,
                    r.total_rows,
                    r.mapped_rows,
                    r.row_coverage_pct,
                    r.distinct_codes,
                    r.mapped_codes,
                    r.code_coverage_pct,
                )
                for r in rows
            ],
        )
    conn.execute("DELETE FROM etl_meta.unmapped_codes WHERE run_id = %s", (run_id,))
    unmapped = top_unmapped(conn, limit=50)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO etl_meta.unmapped_codes "
            "(run_id, source_system, domain, source_code, row_count) "
            "VALUES (%s, 'synthea', %s, %s, %s)",
            [(run_id, domain, code, n) for domain, code, n in unmapped],
        )
    conn.commit()
    return len(rows)


def compute_and_report(conn: psycopg.Connection) -> list[CoverageRow]:
    write_coverage_table(conn)
    return compute_coverage(conn)
