.PHONY: setup check lint test test-network secret-scan smoke demo up down logs fmt ci

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

demo:
	@test -f scripts/demo.py || (echo "make demo: scripts/demo.py not built yet (T-005)" && exit 1)
	uv run python scripts/demo.py

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

ci:
	./scripts/ci.sh
