from pathlib import Path

import pytest

from tracemap.load import ddl, vocab

VOCABULARY_HEADER = (
    "vocabulary_id\tvocabulary_name\tvocabulary_reference\tvocabulary_version\t"
    "vocabulary_concept_id\n"
)


def write_vocabulary_csv(folder: Path, vocabulary_ids: list[str]) -> None:
    rows = [f"{v}\t{v} name\t\t{v} v1\t0\n" for v in vocabulary_ids]
    (folder / "VOCABULARY.csv").write_text(VOCABULARY_HEADER + "".join(rows), encoding="utf-8")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"header\n", 0),
        (b"header\na\nb\n", 2),
        (b"header\na\nb", 2),  # no trailing newline on the last row
        (b"", 0),
    ],
)
def test_count_data_rows(tmp_path, content, expected):
    path = tmp_path / "x.csv"
    path.write_bytes(content)
    assert vocab.count_data_rows(path) == expected


def test_check_download_reports_missing_files_and_vocabularies(tmp_path):
    write_vocabulary_csv(tmp_path, ["SNOMED", "LOINC"])
    problems = vocab.check_download(tmp_path)
    assert "Missing file: CONCEPT.csv" in problems
    assert "Missing vocabulary: ICD10" in problems
    assert "Missing vocabulary: SNOMED" not in problems


def test_check_download_passes_when_complete(tmp_path):
    write_vocabulary_csv(tmp_path, [*vocab.REQUIRED_VOCABULARIES, "None"])
    for file_name in vocab.VOCAB_FILES:
        if file_name != "VOCABULARY.csv":
            (tmp_path / file_name).write_text("header\n", encoding="utf-8")
    assert vocab.check_download(tmp_path) == []


def test_vocabulary_release_reads_the_none_row(tmp_path):
    (tmp_path / "VOCABULARY.csv").write_text(
        VOCABULARY_HEADER + "None\tOMOP Standardized Vocabularies\t\tv5.0 29-AUG-26\t44819096\n",
        encoding="utf-8",
    )
    assert vocab.vocabulary_release(tmp_path) == "v5.0 29-AUG-26"


def test_every_vocab_table_file_maps_to_a_vocab_schema_table():
    for table in vocab.VOCAB_FILES.values():
        assert ddl.schema_for_table(table) == "vocab"


def test_vocab_index_statements_skip_cluster_and_cdm_tables():
    statements = ddl.index_statements("vocab")
    assert statements
    assert all(" ON vocab." in s for s in statements)
    assert not any(s.upper().startswith("CLUSTER") for s in statements)
