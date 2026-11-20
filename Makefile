.PHONY: setup check lint test test-network secret-scan smoke demo wallets api worker up down logs fmt ci

setup:
	uv sync
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example: set JWT_SECRET")

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest -m "not network"

test-network:
	uv run pytest -m network

secret-scan:
	uv run python -I scripts/secret_scan.py

check: lint test secret-scan

smoke:
	uv run ixh26 smoke

# Local (non-docker) runs read .env; docker compose loads it on its own.
wallets:
	uv run --env-file .env python scripts/new_wallets.py

demo: wallets
	uv run --env-file .env python scripts/demo.py $(ARGS)

api:
	@mkdir -p data
	uv run --env-file .env ixh26 api --host 127.0.0.1 --port 8000

worker:
	@mkdir -p data
	uv run --env-file .env ixh26 worker

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

ci:
	./scripts/ci.sh
