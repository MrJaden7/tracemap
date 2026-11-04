"""TraceMap command line interface.

This is also the project's task runner: every pipeline step is a command here, so the
pipeline runs the same way on Windows, macOS and Linux. The Makefile is a thin set of
aliases over these commands.
"""

import typer
from rich.console import Console

from tracemap.db import connect
from tracemap.load import ddl

app = typer.Typer(help="TraceMap: documentation-first OMOP CDM pipeline.", no_args_is_help=True)
db_app = typer.Typer(help="Database setup commands.", no_args_is_help=True)
app.add_typer(db_app, name="db")

console = Console()


@db_app.command("init")
def db_init(
    reset: bool = typer.Option(False, "--reset", help="Drop and recreate all TraceMap schemas."),
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
    """Apply OHDSI CDM indices (run after loading data)."""
    with connect() as conn:
        count = ddl.apply_indices(conn)
    console.print(f"Applied {count} index statements.")


if __name__ == "__main__":
    app()
