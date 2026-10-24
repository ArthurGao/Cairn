# Entry points (AGENTS.md "Commands"). Ports are fixed: API 4700, web 4710, Temporal 7233/8233.
.PHONY: install dev dev-temporal dev-worker dev-api dev-web check check-backend check-frontend test e2e-full

install:
	cd backend && uv sync
	cd frontend && npm ci && npx playwright install chromium

# Temporal + worker + API + web in parallel; Ctrl-C stops all of them.
dev:
	$(MAKE) -j4 dev-temporal dev-worker dev-api dev-web

dev-temporal:
	mkdir -p .temporal
	temporal server start-dev --db-filename .temporal/dev.db --port 7233 --ui-port 8233

dev-worker:
	cd backend && uv run python -m cairn.worker

dev-api:
	cd backend && uv run uvicorn cairn.api.app:create_app --factory --port 4700 --reload

dev-web:
	cd frontend && npm run dev

# Every gate; must exit 0 before a task is called done.
check: check-backend check-frontend

check-backend:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd backend && uv run pyright
	cd backend && uv run pytest

check-frontend:
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run test
	cd frontend && npm run api:check

test:
	cd backend && uv run pytest
	cd frontend && npm run test

# Real stack on the standard ports with the fake vendor; refuses if a port is taken.
e2e-full:
	./scripts/e2e_full.sh
