# Makefile

.PHONY: up down test lint migrate worker api ops-token

up:
	docker compose up -d

down:
	docker compose down

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run black --check . && uv run mypy --strict src && uv run lint-imports

migrate:
	cd backend && uv run alembic upgrade head

worker:
	cd backend && uv run arq naka.worker.WorkerSettings

api:
	cd backend && uv run uvicorn naka.main:app --reload --app-dir src

ops-token:
	cd backend && uv run python scripts/mint_ops_token.py
