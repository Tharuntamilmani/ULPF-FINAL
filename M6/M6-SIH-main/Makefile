# ═══════════════════════════════════════════════════════════════════════════════
# ULPF M6 Control Plane — Makefile
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help install dev up down logs test lint format typecheck \
        contract-test integration-test seed e2e airgap clean \
        migrate migrate-down db-reset build push trivy

BACKEND_DIR := backend
FRONTEND_DIR := frontend
DC          := docker compose
PYTEST      := python -m pytest
RUFF        := python -m ruff
MYPY        := python -m mypy

# ── Default target ─────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  ULPF M6 Control Plane"
	@echo "  ─────────────────────────────────────────────────────────────────"
	@echo "  make install          Install Python + Node deps"
	@echo "  make dev              Run FastAPI dev server locally (no Docker)"
	@echo "  make up               docker compose up -d (M6 + infra)"
	@echo "  make down             docker compose down"
	@echo "  make logs             Tail compose logs"
	@echo "  make test             Run all tests"
	@echo "  make lint             Ruff lint"
	@echo "  make format           Ruff format"
	@echo "  make typecheck        mypy check"
	@echo "  make contract-test    Run JSON-schema contract tests only"
	@echo "  make integration-test Run integration tests (needs running infra)"
	@echo "  make seed             Seed database with M6 bootstrap data"
	@echo "  make e2e              Run E2E tests against running M6 (mocked M1-M5)"
	@echo "  make airgap           Build air-gapped deployment package"
	@echo "  make migrate          Run Alembic migrations"
	@echo "  make migrate-down     Rollback last migration"
	@echo "  make db-reset         Drop + recreate DB + run migrations + seed"
	@echo "  make build            Build Docker image"
	@echo "  make trivy            Run Trivy vulnerability scan"
	@echo "  make clean            Remove build artefacts and caches"
	@echo ""

# ── Install ────────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm install

# ── Local dev (no Docker) ──────────────────────────────────────────────────────
dev:
	@echo "Starting M6 backend dev server..."
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# ── Docker Compose ─────────────────────────────────────────────────────────────
up:
	$(DC) up -d
	@echo ""
	@echo "  M6 Control Plane is starting..."
	@echo "  API:      http://localhost:8000"
	@echo "  Docs:     http://localhost:8000/docs"
	@echo "  Frontend: http://localhost:5173  (run 'make dev-frontend' locally)"
	@echo "  Grafana:  http://localhost:3000"
	@echo "  Prometheus: http://localhost:9090"
	@echo ""

down:
	$(DC) down

down-volumes:
	$(DC) down -v

logs:
	$(DC) logs -f

logs-api:
	$(DC) logs -f m6-api

# ── Migrations ─────────────────────────────────────────────────────────────────
migrate:
	cd $(BACKEND_DIR) && alembic upgrade head

migrate-down:
	cd $(BACKEND_DIR) && alembic downgrade -1

migrate-history:
	cd $(BACKEND_DIR) && alembic history --verbose

db-reset: down-volumes up
	@sleep 8
	$(MAKE) migrate
	$(MAKE) seed

# ── Seed ───────────────────────────────────────────────────────────────────────
seed:
	python scripts/seed.py

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -v

test-unit:
	$(PYTEST) tests/unit/ -v

test-api:
	$(PYTEST) tests/api/ -v

contract-test:
	$(PYTEST) tests/contract/ -v -s

integration-test:
	$(PYTEST) tests/integration/ -v -s

e2e:
	@echo "Running E2E tests against M6 (mocked M1-M5 adapters)..."
	USE_MOCK_ADAPTERS=true $(PYTEST) tests/ -v -s --timeout=60

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	$(RUFF) check backend/ tests/
	cd $(FRONTEND_DIR) && npm run lint

format:
	$(RUFF) check --fix backend/ tests/
	$(RUFF) format backend/ tests/
	cd $(FRONTEND_DIR) && npm run format

typecheck:
	$(MYPY) backend/app --ignore-missing-imports

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	docker build -t ulpf/m6-control-plane:latest .

push:
	docker push ulpf/m6-control-plane:latest

trivy:
	trivy image ulpf/m6-control-plane:latest

# ── Air-gap ────────────────────────────────────────────────────────────────────
airgap:
	bash deployment/airgapped/package-airgap.sh

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov coverage.xml .coverage
	cd $(FRONTEND_DIR) && rm -rf dist node_modules/.vite 2>/dev/null || true
