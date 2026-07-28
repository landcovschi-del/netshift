# For WSL 2 / Linux / macOS. On native Windows use .\make.ps1 instead:
# GNU make is not available there, and the targets below rely on bash.

SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help setup up down reset test cov lint fmt typecheck check doctor demo clean

help: ## show this list
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## create .env and install dependencies
	@test -f .env || (cp .env.example .env && echo ".env created -- put your keys there")
	uv sync

up: ## start Postgres and wait until healthy
	docker compose up -d
	@echo "waiting for Postgres to become healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' netshift-postgres 2>/dev/null)" = "healthy" ]; do \
		sleep 2; \
	done
	@echo "Postgres accepts connections"

down: ## stop containers (data is kept)
	docker compose down

reset: ## stop containers and DELETE the data volume
	docker compose down -v

test: ## run tests
	uv run pytest

cov: ## run tests with a coverage report
	uv run pytest --cov=netshift --cov-report=term-missing

lint: ## ruff check
	uv run ruff check .

fmt: ## ruff format + autofixes
	uv run ruff format .
	uv run ruff check --fix .

typecheck: ## mypy in strict mode
	uv run mypy

check: lint typecheck test ## same as CI

doctor: ## environment report
	uv run netshift doctor

demo: ## inspect every file under samples/
	@for f in samples/*.csproj; do uv run netshift inspect "$$f" || true; done

clean: ## remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build
	find . -path ./.venv -prune -o -name __pycache__ -type d -exec rm -rf {} +
