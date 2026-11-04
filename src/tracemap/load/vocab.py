"""Load OMOP Standardized Vocabularies downloaded from Athena into the vocab schema.

Steps:
1. Check every expected file is present and every required vocabulary is in VOCABULARY.csv.
2. Truncate and bulk load each table with Postgres COPY.
3. Compare loaded row counts with the row counts in the source files. Any mismatch fails.
4. Create indexes (OHDSI's plus the ones the mapping SQL relies on).
5. Record what was loaded, and the vocabulary version, in etl_meta.vocabulary_load.

Athena files are tab-separated despite the .csv extension, and concept names can contain
double quotes. COPY is therefore told to use tab as the delimiter and a backspace as the
quote character, which never appears in the data, so quotes are kept as literal text.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import psycopg

from tracemap.load import ddl

# Athena file name -> vocab table. Order matters only for readability of the log.
VOCAB_FILES: dict[str, str] = {
    "VOCABULARY.csv": "vocabulary",
    "DOMAIN.csv": "domain",
    "CONCEPT_CLASS.csv": "concept_class",
    "RELATIONSHIP.csv": "relationship",
    "CONCEPT.csv": "concept",
    "CONCEPT_SYNONYM.csv": "concept_synonym",
    "CONCEPT_RELATIONSHIP.csv": "concept_relationship",
    "CONCEPT_ANCESTOR.csv": "concept_ancestor",
    "DRUG_STRENGTH.csv": "drug_strength",
}

# Files Athena now ships that are not part of the OMOP CDM v5.4 DDL. Skipped on purpose.
IGNORED_FILES = frozenset(
    {"CONCEPT_METADATA.csv", "CONCEPT_RELATIONSHIP_METADATA.csv", "PACK_CONTENT.csv"}
)

# Vocabularies TraceMap's mappings depend on. The load stops if any is missing.
REQUIRED_VOCABULARIES = (
    "SNOMED",
    "ICD10",
    "OPCS4",
    "dm+d",
    "RxNorm",
    "RxNorm Extension",
    "LOINC",
    "UCUM",
    "CVX",
    "Gender",
    "Race",
    "Ethnicity",
    "Visit",
    "Type Concept",
    "Domain",
    "Vocabulary",
    "Concept Class",
    "Relationship",
)

# Composite indexes for the lookups the generated mapping SQL performs. OHDSI's index file
# only has single-column indexes on these tables.
EXTRA_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_concept_code_vocab "
    "ON vocab.concept (concept_code, vocabulary_id)",
    "CREATE INDEX IF NOT EXISTS idx_concept_relationship_id1_rel "
    "ON vocab.concept_relationship (concept_id_1, relationship_id)",
)

COPY_OPTIONS = "FORMAT csv, DELIMITER E'\\t', QUOTE E'\\b', HEADER true, NULL ''"
CHUNK_SIZE = 8 * 1024 * 1024


class VocabularyError(Exception):
    """The vocabulary download is incomplete or did not load correctly."""


@dataclass(frozen=True)
class LoadResult:
    table: str
    file_name: str
    file_rows: int
    loaded_rows: int


def read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return f.readline().rstrip("\r\n").split("\t")


def count_data_rows(path: Path) -> int:
    """Count data lines (excluding the header) without loading the file into memory."""
    newlines = 0
    last = b"\n"
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            newlines += chunk.count(b"\n")
            last = chunk[-1:]
    lines = newlines + (0 if last == b"\n" else 1)
    return max(lines - 1, 0)


def read_vocabulary_ids(vocab_dir: Path) -> dict[str, str]:
    """vocabulary_id -> vocabulary_version, read from VOCABULARY.csv."""
    with (vocab_dir / "VOCABULARY.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        return {row["vocabulary_id"]: row["vocabulary_version"] for row in reader}


def vocabulary_release(vocab_dir: Path) -> str:
    """The overall Athena release, stored on the special 'None' vocabulary row."""
    return read_vocabulary_ids(vocab_dir).get("None", "unknown")


def check_download(vocab_dir: Path) -> list[str]:
    """Return a list of problems with the download. Empty means it is ready to load."""
    problems = []
    for file_name in VOCAB_FILES:
        if not (vocab_dir / file_name).is_file():
            problems.append(f"Missing file: {file_name}")
    if (vocab_dir / "VOCABULARY.csv").is_file():
        present = read_vocabulary_ids(vocab_dir)
        problems.extend(
            f"Missing vocabulary: {v}" for v in REQUIRED_VOCABULARIES if v not in present
        )
    return problems


def load_table(conn: psycopg.Connection, path: Path, table: str) -> LoadResult:
    columns = ", ".join(read_header(path))
    conn.execute(f"TRUNCATE vocab.{table}")
    copy_sql = f"COPY vocab.{table} ({columns}) FROM STDIN WITH ({COPY_OPTIONS})"
    with conn.cursor() as cur, path.open("rb") as f, cur.copy(copy_sql) as copy:
        while chunk := f.read(CHUNK_SIZE):
            copy.write(chunk)
    row = conn.execute(f"SELECT count(*) FROM vocab.{table}").fetchone()
    loaded_rows = row[0] if row else 0
    file_rows = count_data_rows(path)
    if loaded_rows != file_rows:
        raise VocabularyError(f"{table}: file has {file_rows} rows but {loaded_rows} were loaded")
    return LoadResult(table, path.name, file_rows, loaded_rows)


def create_indexes(conn: psycopg.Connection) -> int:
    count = ddl.apply_indices(conn, schema="vocab")
    for statement in EXTRA_INDEXES:
        conn.execute(statement)
    conn.execute("ANALYZE")
    return count + len(EXTRA_INDEXES)


def record_load(conn: psycopg.Connection, results: list[LoadResult], release: str) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO etl_meta.vocabulary_load "
            "(table_name, file_name, file_rows, loaded_rows, vocabulary_version) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(r.table, r.file_name, r.file_rows, r.loaded_rows, release) for r in results],
        )
