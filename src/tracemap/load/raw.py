"""Raw loader.

Loads source CSV files into the `raw` schema as text, one table per file. Each row keeps
a `_source_row` number so later lineage can point back to the exact line in the source
file, and a `_run_id` tying the row to the ETL run that loaded it. A SHA-256 checksum is
recorded for every file in `raw.load_manifest`, so a changed input is detectable.
"""

import csv
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import psycopg

from tracemap.synthea import SYNTHEA_JAR_SHA256, SYNTHEA_VERSION

CHUNK_SIZE = 8 * 1024 * 1024
RESERVED_COLUMNS = ("_source_row", "_run_id")


@dataclass(frozen=True)
class CsvFile:
    path: Path
    table: str  # fully qualified, e.g. raw.synthea_patients


@dataclass(frozen=True)
class LoadedFile:
    file: CsvFile
    sha256: str
    size_bytes: int
    row_count: int


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return None


def discover_synthea_csvs(csv_dir: Path) -> list[CsvFile]:
    return [
        CsvFile(path=p, table=f"raw.synthea_{p.stem.lower()}")
        for p in sorted(csv_dir.glob("*.csv"))
    ]


def discover_uk_csvs(csv_dir: Path) -> list[CsvFile]:
    """UK extract files are named uk_*.csv and load into raw.uk_* tables."""
    return [
        CsvFile(path=p, table=f"raw.{p.stem.lower()}") for p in sorted(csv_dir.glob("uk_*.csv"))
    ]


def read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def quote_ident(name: str) -> str:
    """Quote a Postgres identifier."""
    return '"' + name.replace('"', '""') + '"'


def create_raw_table(conn: psycopg.Connection, csv_file: CsvFile) -> None:
    """Create raw.synthea_<name> if it does not exist, columns derived from the CSV header."""
    header = read_header(csv_file.path)
    for name in header:
        if name.lower() in RESERVED_COLUMNS:
            raise ValueError(f"Reserved column name {name} in {csv_file.path}")
    column_defs = ",\n    ".join(f"{quote_ident(name.lower())} text" for name in header)
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {csv_file.table} (\n"
        f"    {column_defs},\n"
        f"    _source_row bigint NOT NULL,\n"
        f"    _run_id     bigint NOT NULL\n"
        f")"
    )


def count_data_rows(path: Path) -> int:
    newlines = 0
    last = b"\n"
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            newlines += chunk.count(b"\n")
            last = chunk[-1:]
    lines = newlines + (0 if last == b"\n" else 1)
    return max(lines - 1, 0)


def load_csv(conn: psycopg.Connection, csv_file: CsvFile, run_id: int) -> LoadedFile:
    """Truncate the target table and COPY the CSV into it with row number and run id."""
    header = read_header(csv_file.path)
    data_columns = [quote_ident(name.lower()) for name in header]
    # COPY into a server-side temp table, then insert with added columns. Drop before
    # creating because the same transaction will stage multiple files one after another.
    conn.execute(f"TRUNCATE {csv_file.table}")
    conn.execute("DROP TABLE IF EXISTS _stage")
    stage_cols = ", ".join(f"{c} text" for c in data_columns)
    conn.execute(f"CREATE TEMP TABLE _stage ({stage_cols})")
    with conn.cursor() as cur, csv_file.path.open("rb") as f:
        copy_sql = (
            f"COPY _stage ({', '.join(data_columns)}) FROM STDIN "
            "WITH (FORMAT csv, HEADER true, NULL '')"
        )
        with cur.copy(copy_sql) as copy:
            while chunk := f.read(CHUNK_SIZE):
                copy.write(chunk)
    inserted = conn.execute(
        f"INSERT INTO {csv_file.table} ({', '.join(data_columns)}, _source_row, _run_id) "
        f"SELECT {', '.join(data_columns)}, "
        f"       row_number() OVER () AS _source_row, "
        f"       %s AS _run_id "
        f"FROM _stage",
        (run_id,),
    ).rowcount
    conn.execute("DROP TABLE _stage")
    file_rows = count_data_rows(csv_file.path)
    if inserted != file_rows:
        raise RuntimeError(
            f"{csv_file.table}: file has {file_rows} rows but {inserted} were loaded"
        )
    return LoadedFile(
        file=csv_file,
        sha256=sha256_of(csv_file.path),
        size_bytes=csv_file.path.stat().st_size,
        row_count=inserted,
    )


def start_run(conn: psycopg.Connection, **kwargs: object) -> int:
    columns = ["git_commit", "synthea_version", "synthea_seed", "synthea_jar_sha256"]
    values = [git_commit(), SYNTHEA_VERSION, kwargs.get("synthea_seed"), SYNTHEA_JAR_SHA256]
    row = conn.execute(
        f"INSERT INTO etl_meta.cdm_run ({', '.join(columns)}) "
        f"VALUES ({', '.join(['%s'] * len(columns))}) RETURNING run_id",
        values,
    ).fetchone()
    return int(row[0])  # type: ignore[index]


def finish_run(conn: psycopg.Connection, run_id: int, status: str = "completed") -> None:
    conn.execute(
        "UPDATE etl_meta.cdm_run SET finished_at = now(), status = %s WHERE run_id = %s",
        (status, run_id),
    )


def record_manifest(
    conn: psycopg.Connection, run_id: int, source_system: str, loaded: list[LoadedFile]
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO raw.load_manifest "
            "(run_id, source_system, target_table, file_name, file_path, "
            " file_sha256, file_size_bytes, row_count) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    run_id,
                    source_system,
                    lf.file.table,
                    lf.file.path.name,
                    str(lf.file.path),
                    lf.sha256,
                    lf.size_bytes,
                    lf.row_count,
                )
                for lf in loaded
            ],
        )
