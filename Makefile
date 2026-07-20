# ── NVIDIA NIM Gateway — Makefile ──────────────────────────────────────
.PHONY: help install dev test lint e2e run docker-build docker-up docker-down clean format

SHELL := /bin/bash

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r backend/requirements.txt

dev: ## Run in development mode with hot reload
	cd backend && uvicorn nim_gateway.main:app --reload --host 0.0.0.0 --port 8000

run: ## Run in production mode
	cd backend && uvicorn nim_gateway.main:app --host 0.0.0.0 --port 8000

test: ## Run tests
	PYTHONPATH=. python3 -m pytest backend/tests/ -v --tb=short --asyncio-mode=auto

lint: ## Run linting
	ruff check backend/ --fix
	ruff format backend/ --check

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files || true

e2e: ## Run end-to-end integration tests
	docker compose -f docker/docker-compose.yml up -d
	@sleep 5
	python -m pytest tests/e2e/ -v || true
	docker compose -f docker/docker-compose.yml down

format: ## Format code
	ruff format backend/

docker-build: ## Build Docker image
	docker compose -f docker/docker-compose.yml build

docker-up: ## Start all services
	docker compose -f docker/docker-compose.yml up -d

docker-up-mon: ## Start with monitoring stack
	docker compose -f docker/docker-compose.yml --profile monitoring up -d

docker-up-all: ## Start everything (monitoring + cache)
	docker compose -f docker/docker-compose.yml --profile monitoring --profile cache up -d

docker-down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

clean: ## Clean Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '.coverage' -delete
	rm -rf .pytest_cache/ htmlcov/ build/ dist/ *.egg-info/

gen-key: ## Generate a secure API key
	python3 -c "from nim_gateway.core.security import generate_api_key; print(generate_api_key())"
