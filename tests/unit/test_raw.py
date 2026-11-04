from pathlib import Path

import pytest

from tracemap.load import raw


def test_discover_synthea_csvs_names_tables_from_filenames(tmp_path: Path) -> None:
    (tmp_path / "patients.csv").write_text("Id\nx\n")
    (tmp_path / "conditions.csv").write_text("CODE\ny\n")
    (tmp_path / "ignored.txt").write_text("should not match")
    files = raw.discover_synthea_csvs(tmp_path)
    assert [(f.path.name, f.table) for f in files] == [
        ("conditions.csv", "raw.synthea_conditions"),
        ("patients.csv", "raw.synthea_patients"),
    ]


def test_read_header_returns_lowercase_safe_columns(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("Id,CODE,description\nrow1,row2,row3\n")
    assert raw.read_header(path) == ["Id", "CODE", "description"]


def test_count_data_rows_excludes_header(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("a,b\n1,2\n3,4\n")
    assert raw.count_data_rows(path) == 2


def test_quote_ident_escapes_double_quotes() -> None:
    assert raw.quote_ident("a") == '"a"'
    assert raw.quote_ident('a"b') == '"a""b"'


def test_sha256_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_bytes(b"hello world")
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert raw.sha256_of(path) == expected


def test_create_raw_table_rejects_reserved_column_name(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("id,_source_row\na,b\n")

    class DummyConn:
        def execute(self, *_, **__):
            raise AssertionError("should not be called")

    with pytest.raises(ValueError, match="Reserved column name"):
        raw.create_raw_table(DummyConn(), raw.CsvFile(path=path, table="raw.x"))
