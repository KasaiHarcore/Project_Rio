.PHONY: help install dev serve docker-build docker-up docker-down docker-logs \
       migrate-new migrate-up migrate-down migrate-history \
       lint format type-check test test-cov clean ci-local

# ── Help ────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Dev
# ============================================================================
install: ## Install all dependencies (including dev)
	uv sync --locked

dev: ## Run FastAPI with hot-reload
	PYTHONPATH=src uvicorn core.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

serve: ## Run Streamlit UI
	PYTHONPATH=src streamlit run src/interfaces/demo/chat_main.py

# ============================================================================
# Docker
# ============================================================================
docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

# ============================================================================
# Database Migrations (Alembic)
# ============================================================================
migrate-new: ## Create new migration (usage: make migrate-new msg="add users table")
	PYTHONPATH=src alembic revision --autogenerate -m "$(msg)"

migrate-up: ## Apply all pending migrations
	PYTHONPATH=src alembic upgrade head

migrate-down: ## Rollback last migration
	PYTHONPATH=src alembic downgrade -1

migrate-history: ## Show migration history
	PYTHONPATH=src alembic history --verbose

# ============================================================================
# Code Quality
# ============================================================================
lint: ## Run linter (ruff)
	ruff check src/

format: ## Format code (ruff)
	ruff format src/

type-check: ## Run type checker (mypy)
	mypy src/

test: ## Run tests
	PYTHONPATH=src pytest tests/ -v

test-cov: ## Run tests with coverage
	PYTHONPATH=src pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

# ============================================================================
# Utility
# ============================================================================
clean: ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

ci-local: lint type-check test ## Run full CI pipeline locally
