"""The spec requires a full rebuild to produce identical output. This test rebuilds the
CDM tables through dbt twice and checks every CDM table's md5 checksum is identical.

Long-running: skipped by default unless run via `pytest -m integration slow`.
"""

import os
import subprocess
from pathlib import Path

import pytest

from tracemap.config import REPO_ROOT, get_settings
from tracemap.db import connect

pytestmark = pytest.mark.integration

DBT_DIR = REPO_ROOT / "dbt"


CDM_TABLES = [
    "person",
    "observation_period",
    "visit_occurrence",
    "condition_occurrence",
    "drug_exposure",
    "procedure_occurrence",
    "death",
    "location",
    "care_site",
    "provider",
]


def table_checksum(conn, table: str) -> str:
    """md5 of concatenated CSV-like row text, ordered by primary key."""
    key = f"{table}_id"
    if table == "death":
        key = "person_id"
    rows = conn.execute(
        f"SELECT md5(string_agg(t::text, ',' ORDER BY t.{key})) FROM cdm.{table} t"
    ).fetchone()
    return rows[0] if rows else ""


def _run_dbt(subcmd: str) -> None:
    env = {
        **os.environ,
        "DBT_PROFILES_DIR": str(DBT_DIR),
        "TRACEMAP_DB_NAME": get_settings().db_name,
    }
    cmd = [str(Path(".venv/Scripts/dbt" if os.name == "nt" else ".venv/bin/dbt"))]
    cmd += [subcmd, "--project-dir", str(DBT_DIR)]
    subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=True)


@pytest.mark.slow
def test_full_rebuild_produces_identical_tables():
    _run_dbt("run")
    with connect() as conn:
        first = {t: table_checksum(conn, t) for t in CDM_TABLES}
    _run_dbt("run")
    with connect() as conn:
        second = {t: table_checksum(conn, t) for t in CDM_TABLES}
    for t in CDM_TABLES:
        assert first[t] == second[t], f"cdm.{t} changed across rebuild: {first[t]} vs {second[t]}"
