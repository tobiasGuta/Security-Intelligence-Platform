.PHONY: up down build logs migrate create-admin seed format lint typecheck test-unit test-integration test-frontend test-e2e clean help

COMPOSE = docker compose
API = $(COMPOSE) exec api

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	$(COMPOSE) up -d

build: ## Build all images
	$(COMPOSE) build

down: ## Stop all services
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f

migrate: ## Run Alembic migrations
	$(API) python -m alembic upgrade head

create-admin: ## Create admin user (prompts for credentials)
	$(API) python -m app.cli create-admin

seed: ## Seed development data
	$(API) python -m app.cli seed-dev

format: ## Format Python and frontend code
	$(COMPOSE) run --rm api uv run ruff format .
	cd apps/web && npx prettier --write .

lint: ## Lint Python and frontend code
	$(COMPOSE) run --rm api bash -c "ruff check . && mypy app"
	cd apps/web && npm run lint

typecheck: ## Run TypeScript type check
	cd apps/web && npm run type-check

test-unit: ## Run backend unit tests
	$(COMPOSE) --profile test up -d postgres-test redis-test
	$(COMPOSE) run --rm -e APP_ENV=testing -e TEST_DATABASE_URL=postgresql+asyncpg://sip:sip_test_password@postgres-test:5432/sip_test -e REDIS_URL=redis://:sip_test_password@redis-test:6379/1 api bash -c "pytest tests/unit -v --tb=short"
	$(COMPOSE) --profile test down

test-integration: ## Run backend integration tests (requires running postgres + redis)
	$(COMPOSE) --profile test up -d postgres-test redis-test
	$(COMPOSE) run --rm -e APP_ENV=testing -e TEST_DATABASE_URL=postgresql+asyncpg://sip:sip_test_password@postgres-test:5432/sip_test -e REDIS_URL=redis://:sip_test_password@redis-test:6379/1 api bash -c "pytest tests/integration -v --tb=short"
	$(COMPOSE) --profile test down

test-frontend: ## Run frontend unit tests
	cd apps/web && npm test

test-e2e: ## Run Playwright end-to-end tests
	cd apps/web && npm run test:e2e

clean: ## Remove all containers, volumes, and built images
	$(COMPOSE) down -v --rmi local
