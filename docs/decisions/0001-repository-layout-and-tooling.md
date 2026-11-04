# ADR 0001: Repository layout and tooling

- Status: Accepted
- Date: 2026-11-04

## Context

TraceMap will be read by a hiring panel and must run from a clean clone on Windows, macOS and Linux (including GitHub Actions). The project brief proposed a layout with the pydantic schema inside `mapping_spec/` and a Makefile as the entry point.

## Decision

1. **`src/` layout.** Python code lives in `src/tracemap/` and is installed into the project environment. Tests run against the installed package, not whatever happens to be on the path, which catches packaging mistakes early.
2. **`mapping_spec/` holds YAML only.** The pydantic models that validate it live in the package (`src/tracemap/spec/`). Data and code are kept apart.
3. **uv for environments.** `pyproject.toml` declares dependencies and `uv.lock` pins every version, so a clean clone gets exactly the same environment.
4. **The CLI is the task runner.** Every pipeline step is a `tracemap` command (Typer). The Makefile only contains short aliases such as `make db-init` for `uv run tracemap db init`. Anyone without `make`, which includes most Windows machines, runs the same commands with `uv run tracemap ...`.
5. **Postgres 16 in Docker Compose on host port 5440.** 5440 avoids clashing with other local Postgres instances on 5432 and 5433.
6. **Line endings normalised to LF** with `.gitattributes`, so the Makefile and SQL behave the same in CI on Linux.

## Alternatives considered

- **Flat layout (`tracemap/` at the repo root):** simpler, but tests can pass by importing local files that would be missing from an installed package.
- **Makefile as the only entry point:** standard on Linux, but needs extra installs on Windows, and Make syntax is harder for reviewers to read than Python.
- **A separate task runner (poethepoet, nox, invoke):** adds a tool without adding value, since the CLI already has to exist for `tracemap trace`.
- **pip and requirements.txt:** works, but no lock file by default, so builds are less reproducible.

## Consequences

- One place to look for every pipeline step: `src/tracemap/cli.py`.
- Contributors need uv installed. This is documented in the README.

## In plain English

The code is organised the way a professional Python project is, every step can be run with one command on any operating system, and the exact versions of every library are locked so results are reproducible.
