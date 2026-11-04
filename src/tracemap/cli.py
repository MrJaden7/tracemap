"""TraceMap command line interface.

This is also the project's task runner: every pipeline step is a command here, so the
pipeline runs the same way on Windows, macOS and Linux. The Makefile is a thin set of
aliases over these commands.
"""

import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from tracemap.config import get_settings
from tracemap.db import connect
from tracemap.load import ddl, vocab

app = typer.Typer(help="TraceMap: documentation-first OMOP CDM pipeline.", no_args_is_help=True)
db_app = typer.Typer(help="Database setup commands.", no_args_is_help=True)
vocab_app = typer.Typer(help="OMOP vocabulary commands.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(vocab_app, name="vocab")

console = Console()

VocabPathOption = Annotated[
    Path | None, typer.Option(help="Folder with the unzipped Athena download.")
]


@db_app.command("init")
def db_init(
    reset: Annotated[
        bool, typer.Option("--reset", help="Drop and recreate all TraceMap schemas.")
    ] = False,
) -> None:
    """Create schemas and apply the official OMOP CDM v5.4 DDL with primary keys."""
    with connect() as conn:
        if ddl.cdm_tables_exist(conn) and not reset:
            console.print("CDM tables already exist. Use --reset to drop and recreate.")
            raise typer.Exit(code=0)
        ddl.create_schemas(conn, reset=reset)
        count = ddl.apply_tables_and_primary_keys(conn)
    schemas = ", ".join(ddl.PROJECT_SCHEMAS)
    console.print(f"Created schemas {schemas} and ran {count} DDL statements.")


@db_app.command("indices")
def db_indices() -> None:
    """Apply OHDSI indices to the cdm schema (run after the CDM is built)."""
    with connect() as conn:
        count = ddl.apply_indices(conn, schema="cdm")
    console.print(f"Applied {count} index statements to cdm.")


def _vocab_dir(path: Path | None) -> Path:
    return path or get_settings().vocab_dir


@vocab_app.command("check")
def vocab_check(
    path: VocabPathOption = None,
) -> None:
    """Check the Athena download has every file and vocabulary TraceMap needs."""
    vocab_dir = _vocab_dir(path)
    problems = vocab.check_download(vocab_dir)
    if problems:
        for problem in problems:
            console.print(f"[red]{problem}[/red]")
        raise typer.Exit(code=1)
    release = vocab.vocabulary_release(vocab_dir)
    console.print(f"Vocabulary download OK ({release}) in {vocab_dir}")


@vocab_app.command("load")
def vocab_load(
    path: VocabPathOption = None,
) -> None:
    """Load Athena vocabularies into the vocab schema, verify row counts, build indexes."""
    vocab_dir = _vocab_dir(path)
    problems = vocab.check_download(vocab_dir)
    if problems:
        for problem in problems:
            console.print(f"[red]{problem}[/red]")
        raise typer.Exit(code=1)
    release = vocab.vocabulary_release(vocab_dir)
    console.print(f"Loading vocabulary release {release} from {vocab_dir}")

    results = []
    with connect() as conn:
        for file_name, table in vocab.VOCAB_FILES.items():
            started = time.perf_counter()
            result = vocab.load_table(conn, vocab_dir / file_name, table)
            conn.commit()
            elapsed = time.perf_counter() - started
            console.print(f"  {table:<22} {result.loaded_rows:>12,} rows  {elapsed:6.1f}s")
            results.append(result)

        console.print("Creating indexes...")
        started = time.perf_counter()
        index_count = vocab.create_indexes(conn)
        console.print(f"  {index_count} indexes in {time.perf_counter() - started:.1f}s")
        vocab.record_load(conn, results, release)

    summary = Table(title="Vocabulary load")
    summary.add_column("Table")
    summary.add_column("File rows", justify="right")
    summary.add_column("Loaded rows", justify="right")
    for r in results:
        summary.add_row(r.table, f"{r.file_rows:,}", f"{r.loaded_rows:,}")
    console.print(summary)


if __name__ == "__main__":
    app()
