# Cricksy Scorer - Makefile
# Single Source of Truth for CI and Local Development
# ==============================================================================
# Run exactly what CI runs: make ci
# Full deployment checks: make ci-full
# ==============================================================================

.PHONY: help ci ci-full test lint format install-dev check-versions clean

# Default Python and Node versions (must match .python-version and .nvmrc)
PYTHON_VERSION := 3.12.12
NODE_VERSION := 20.18.1

# Directories
BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV := .venv

# Environment
export PYTHONPATH := $(shell pwd)
export CRICKSY_IN_MEMORY_DB := 1
export DATABASE_URL := sqlite+aiosqlite:///:memory:?cache=shared
export APP_SECRET_KEY := test-secret-key

help: ## Show this help message
	@echo "Cricksy Scorer - Make Commands"
	@echo "==============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check-versions: ## Verify Python and Node versions match pinned versions
	@echo "Checking runtime versions..."
	@python_ver=$$(python --version 2>&1 | cut -d' ' -f2); \
	if [ "$$python_ver" != "$(PYTHON_VERSION)" ]; then \
		echo "❌ Python version mismatch: expected $(PYTHON_VERSION), got $$python_ver"; \
		echo "   Use pyenv or install correct version"; \
		exit 1; \
	else \
		echo "✅ Python $(PYTHON_VERSION)"; \
	fi
	@node_ver=$$(node --version | cut -d'v' -f2); \
	if [ "$$node_ver" != "$(NODE_VERSION)" ]; then \
		echo "❌ Node version mismatch: expected $(NODE_VERSION), got $$node_ver"; \
		echo "   Use nvm or install correct version"; \
		exit 1; \
	else \
		echo "✅ Node $(NODE_VERSION)"; \
	fi

install-dev: ## Install all dependencies (backend + frontend)
	@echo "Installing backend dependencies..."
	python -m pip install --upgrade pip
	pip install -r $(BACKEND_DIR)/requirements.txt
	pip install ruff==0.6.5 mypy==1.11.2 pytest==7.4.3 pre-commit==3.5.0
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm ci

lint: ## Run all linters (ruff + mypy + eslint)
	@echo "=== Backend Lint ==="
	ruff check .
	ruff format --check .
	cd $(BACKEND_DIR) && mypy --config-file pyproject.toml --explicit-package-bases .
	@echo "=== Frontend Lint ==="
	cd $(FRONTEND_DIR) && npm run lint

format: ## Auto-fix formatting issues
	@echo "Formatting backend..."
	ruff check . --fix
	ruff format .
	@echo "Formatting frontend..."
	cd $(FRONTEND_DIR) && npm run format

test: ## Run fast tests (unit tests only, in-memory DB)
	@echo "=== Backend Tests (SQLite in-memory) ==="
	cd $(BACKEND_DIR) && pytest tests/ -v -m "not slow" --tb=short
	@echo "=== Frontend Tests ==="
	cd $(FRONTEND_DIR) && npm run test:unit

test-backend-full: ## Run all backend tests with PostgreSQL
	@echo "=== Backend Tests (requires PostgreSQL) ==="
	@if [ -z "$$DATABASE_URL" ] || [ "$$DATABASE_URL" = "sqlite+aiosqlite:///:memory:?cache=shared" ]; then \
		echo "❌ DATABASE_URL must point to PostgreSQL for full tests"; \
		echo "   Example: export DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/cricksy"; \
		exit 1; \
	fi
	cd $(BACKEND_DIR) && pytest -v

ci: check-versions lint test ## Run CI checks (what GitHub Actions runs)
	@echo ""
	@echo "============================================"
	@echo "✅ All CI checks passed!"
	@echo "============================================"

ci-full: check-versions lint test test-backend-full ## Run full CI including PostgreSQL tests
	@echo ""
	@echo "============================================"
	@echo "✅ Full CI checks passed!"
	@echo "============================================"

clean: ## Remove build artifacts and caches
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	cd $(FRONTEND_DIR) && rm -rf dist node_modules/.cache
	@echo "✅ Cleaned"

.DEFAULT_GOAL := help
