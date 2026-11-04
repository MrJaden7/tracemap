# Thin aliases over the tracemap CLI. Without make, run the same commands with `uv run tracemap ...`.

.PHONY: help setup up down db-init db-reset test test-integration lint

help:
	@echo "setup             install Python environment with uv"
	@echo "up / down         start or stop Postgres in Docker"
	@echo "db-init           create schemas and apply OMOP CDM v5.4 DDL"
	@echo "db-reset          drop and recreate all TraceMap schemas"
	@echo "test              unit tests"
	@echo "test-integration  tests that need Postgres running"
	@echo "lint              ruff and sqlfluff"

setup:
	uv sync

up:
	docker compose up -d --wait

down:
	docker compose down

db-init: up
	uv run tracemap db init

db-reset: up
	uv run tracemap db init --reset

test:
	uv run pytest

test-integration: up
	uv run pytest -m integration

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
