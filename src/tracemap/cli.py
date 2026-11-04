"""TraceMap command line interface.

This is also the project's task runner: every pipeline step is a command here, so the
pipeline runs the same way on Windows, macOS and Linux. The Makefile is a thin set of
aliases over these commands.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from tracemap import synthea as synthea_runner
from tracemap.config import get_settings
from tracemap.db import connect
from tracemap.generate import write_cdm_models, write_schema_tests
from tracemap.lineage import trace_row
from tracemap.load import ddl, raw, vocab
from tracemap.quality import coverage as coverage_mod
from tracemap.spec import load_all_specs

app = typer.Typer(help="TraceMap: documentation-first OMOP CDM pipeline.", no_args_is_help=True)
db_app = typer.Typer(help="Database setup commands.", no_args_is_help=True)
vocab_app = typer.Typer(help="OMOP vocabulary commands.", no_args_is_help=True)
synthea_app = typer.Typer(help="Synthea synthetic data commands.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(vocab_app, name="vocab")
app.add_typer(synthea_app, name="synthea")

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


@db_app.command("migrate")
def db_migrate() -> None:
    """Re-apply the etl_meta/raw DDL (idempotent). Use to add new tables without dropping data."""
    with connect() as conn:
        for statement in ddl.split_statements(ddl.ETL_META_FILE.read_text(encoding="utf-8")):
            conn.execute(statement)
    console.print(f"Applied {ddl.ETL_META_FILE.name}")


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


@synthea_app.command("fetch")
def synthea_fetch() -> None:
    """Download the Synthea jar (pinned version) and verify its SHA-256."""
    settings = get_settings()
    jar = synthea_runner.fetch_jar(settings.synthea_dir)
    console.print(f"Synthea {synthea_runner.SYNTHEA_VERSION} jar ready at {jar}")


@synthea_app.command("generate")
def synthea_generate(
    patients: Annotated[int, typer.Option("--patients", "-p", help="Number of patients.")] = 5000,
    seed: Annotated[int, typer.Option("--seed", "-s", help="Random seed.")] = 42,
    name: Annotated[
        str, typer.Option("--name", help="Subfolder under data/synthea/output.")
    ] = "full",
) -> None:
    """Generate synthetic patient CSVs with a fixed seed."""
    settings = get_settings()
    output = settings.synthea_dir / "output" / name
    console.print(
        f"Generating {patients} patients (seed {seed}, Synthea {synthea_runner.SYNTHEA_VERSION}) "
        f"into {output}"
    )
    run = synthea_runner.generate(settings.synthea_dir, output, patients, seed)
    console.print(
        f"Done. {run.patients} patients requested, jar sha256 {run.jar_sha256[:12]}..., "
        f"output in {run.output_dir}"
    )


raw_app = typer.Typer(help="Raw CSV loader commands.", no_args_is_help=True)
app.add_typer(raw_app, name="raw")


@raw_app.command("load")
def raw_load(
    source: Annotated[
        str, typer.Option("--source", help="Source system name, e.g. synthea.")
    ] = "synthea",
    dir_opt: Annotated[
        Path | None, typer.Option("--dir", help="CSV folder (default full set).")
    ] = None,
    seed: Annotated[int, typer.Option("--seed", help="Synthea seed, recorded in cdm_run.")] = 42,
) -> None:
    """Load CSVs from a source folder into raw.* tables with checksums and a run id."""
    settings = get_settings()
    if dir_opt is None:
        if source != "synthea":
            console.print("[red]--dir is required for non-synthea sources[/red]")
            raise typer.Exit(code=1)
        dir_opt = settings.synthea_dir / "output" / "full" / "csv"
    if not dir_opt.is_dir():
        console.print(f"[red]No such folder: {dir_opt}[/red]")
        raise typer.Exit(code=1)

    csv_files = raw.discover_synthea_csvs(dir_opt)
    if not csv_files:
        console.print(f"[red]No CSV files in {dir_opt}[/red]")
        raise typer.Exit(code=1)

    with connect() as conn:
        run_id = raw.start_run(conn, synthea_seed=seed)
        console.print(f"Run {run_id} started ({source}, {len(csv_files)} files in {dir_opt})")
        loaded = []
        try:
            for csv_file in csv_files:
                raw.create_raw_table(conn, csv_file)
                result = raw.load_csv(conn, csv_file, run_id)
                loaded.append(result)
                console.print(
                    f"  {csv_file.table:<35} {result.row_count:>10,} rows  "
                    f"sha256 {result.sha256[:12]}"
                )
            raw.record_manifest(conn, run_id, source, loaded)
            raw.finish_run(conn, run_id, "completed")
            conn.commit()
        except Exception:
            raw.finish_run(conn, run_id, "failed")
            conn.commit()
            raise
    console.print(f"Run {run_id} completed. Loaded {sum(lf.row_count for lf in loaded):,} rows.")


spec_app = typer.Typer(help="Mapping specification commands.", no_args_is_help=True)
app.add_typer(spec_app, name="spec")


@spec_app.command("check")
def spec_check() -> None:
    """Validate every YAML file in mapping_spec/ and print a summary."""
    specs = load_all_specs()
    for name, spec in sorted(specs.items()):
        fields = sum(len(s.fields) for s in spec.sources)
        sources = ", ".join(spec.source_systems)
        console.print(
            f"  {name:<25} v{spec.spec_version:<6}  {fields:>3} fields  sources: {sources}"
        )
    console.print(f"{len(specs)} specs validated.")


@app.command("generate")
def generate() -> None:
    """Regenerate every dbt CDM model and schema.yml from mapping_spec/*.yml."""
    cdm_paths = write_cdm_models()
    schema_path = write_schema_tests()
    for p in cdm_paths:
        console.print(f"  wrote {p.relative_to(ddl.DDL_FILE.parents[1])}")
    console.print(f"  wrote {schema_path.relative_to(ddl.DDL_FILE.parents[1])}")
    console.print(f"Generated {len(cdm_paths)} CDM models + schema.yml")


@app.command("trace")
def trace(
    cdm_table: Annotated[str, typer.Argument(help="CDM table, e.g. condition_occurrence")],
    cdm_id: Annotated[int, typer.Argument(help="CDM row id to trace")],
) -> None:
    """Trace a CDM row back to its exact source file, row, SHA-256 and run."""
    result = trace_row(cdm_table, cdm_id)
    if result.cdm_row is None:
        console.print(f"[red]No row in cdm.{cdm_table} with id={cdm_id}[/red]")
        raise typer.Exit(code=1)
    sha = result.file_sha256 or "?"
    console.print(f"[bold]cdm.{result.cdm_table}[/bold] id={result.cdm_id}")
    for k, v in result.cdm_row.items():
        if v is not None:
            console.print(f"    {k} = {v}")
    console.print()
    console.print(f"[bold]Source[/bold]: {result.source_table} row {result.source_row}")
    console.print(f"    run_id       = {result.run_id}")
    console.print(f"    file_name    = {result.file_name}")
    console.print(f"    file_sha256  = {sha[:16]}...")
    console.print(f"    file_path    = {result.file_path}")
    console.print()
    if result.source_data:
        console.print("[bold]Source row[/bold]:")
        for k, v in result.source_data.items():
            if v not in (None, "") and k not in ("_source_row", "_run_id"):
                console.print(f"    {k} = {v}")


@app.command("coverage")
def coverage() -> None:
    """Compute and persist mapping coverage per source system and domain."""
    with connect() as conn:
        rows = coverage_mod.compute_and_report(conn)
    if not rows:
        console.print("[yellow]No completed run found. Build the CDM first.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title="Mapping coverage (latest completed run)")
    table.add_column("Source")
    table.add_column("Domain")
    table.add_column("Rows", justify="right")
    table.add_column("Mapped", justify="right")
    table.add_column("Row %", justify="right")
    table.add_column("Codes", justify="right")
    table.add_column("Code %", justify="right")
    for r in rows:
        table.add_row(
            r.source_system,
            r.domain,
            f"{r.total_rows:,}",
            f"{r.mapped_rows:,}",
            f"{r.row_coverage_pct}%",
            f"{r.distinct_codes:,}",
            f"{r.code_coverage_pct}%",
        )
    console.print(table)


@app.command("build")
def build(
    source_dir: Annotated[
        Path | None, typer.Option("--source-dir", help="Synthea CSV folder (default full set).")
    ] = None,
    skip_load: Annotated[bool, typer.Option(help="Skip the raw loader step.")] = False,
    skip_generate: Annotated[bool, typer.Option(help="Skip the model generator.")] = False,
) -> None:
    """End-to-end: load raw -> generate models -> dbt run -> dbt test -> coverage."""
    settings = get_settings()
    if not skip_load:
        csv_dir = source_dir or settings.synthea_dir / "output" / "full" / "csv"
        console.print(f"[bold]1/5 Loading raw from {csv_dir}[/bold]")
        with connect() as conn:
            run_id = raw.start_run(conn)
            loaded = []
            try:
                for csv_file in raw.discover_synthea_csvs(csv_dir):
                    raw.create_raw_table(conn, csv_file)
                    loaded.append(raw.load_csv(conn, csv_file, run_id))
                raw.record_manifest(conn, run_id, "synthea", loaded)
                raw.finish_run(conn, run_id, "completed")
                conn.commit()
            except Exception:
                raw.finish_run(conn, run_id, "failed")
                conn.commit()
                raise

    if not skip_generate:
        console.print("[bold]2/5 Generating dbt models[/bold]")
        write_cdm_models()
        write_schema_tests()

    dbt_dir = ddl.DDL_FILE.parents[1] / "dbt"
    env = {**os.environ, "DBT_PROFILES_DIR": str(dbt_dir)}
    console.print("[bold]3/5 Running dbt[/bold]")
    subprocess.run(["dbt", "run", "--project-dir", str(dbt_dir)], env=env, check=True)
    console.print("[bold]4/5 Testing dbt[/bold]")
    subprocess.run(["dbt", "test", "--project-dir", str(dbt_dir)], env=env, check=True)
    console.print("[bold]5/5 Writing mapping coverage[/bold]")
    with connect() as conn:
        coverage_mod.write_coverage_table(conn)
    console.print("[bold green]Build complete.[/bold green]")


if __name__ == "__main__":
    app()
