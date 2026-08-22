# Makefile

.PHONY: up down test lint migrate

up:
	docker compose up -d

down:
	docker compose down

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run black --check . && uv run mypy --strict src

migrate:
	cd backend && uv run alembic upgrade head
