# Entry points (AGENTS.md "Commands"). Ports are fixed: API 4700, web 4710, Temporal 7233/8233.
.PHONY: install dev dev-temporal temporal-up temporal-down dev-app dev-worker dev-api dev-web check check-repo check-backend check-frontend test e2e-full rehearse

install:
	cd backend && uv sync
	cd frontend && npm ci && npx playwright install chromium

# Temporal + worker + API + web in parallel; Ctrl-C stops all of them.
dev:
	$(MAKE) -j4 dev-temporal dev-worker dev-api dev-web

dev-temporal:
	mkdir -p .temporal
	temporal server start-dev --db-filename .temporal/dev.db --port 7233 --ui-port 8233

# Temporal in Docker instead of the CLI (docker-compose.yml); data persists in a named volume.
temporal-up:
	docker compose up -d --wait temporal

temporal-down:
	docker compose down

# Worker + API + web on the host, against an already running Temporal (e.g. `make temporal-up`).
dev-app:
	$(MAKE) -j3 dev-worker dev-api dev-web

dev-worker:
	cd backend && uv run python -m cairn.worker

dev-api:
	cd backend && uv run uvicorn cairn.api.app:create_app --factory --port 4700 --reload

dev-web:
	cd frontend && npm run dev

# Every gate; must exit 0 before a task is called done.
check: check-repo check-backend check-frontend

# Every *.example template must reach git: a fresh checkout is all the demo VM's setup has.
check-repo:
	@ignored="$$(git ls-files --others --ignored --exclude-standard -- '*.example')"; \
	if [ -n "$$ignored" ]; then echo "git ignores these templates: $$ignored" >&2; exit 1; fi

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

# The demo stack (deploy/oracle) locally in both modes: same images, fake vendor, smoke + full e2e.
rehearse:
	./deploy/oracle/rehearse.sh private
	./deploy/oracle/rehearse.sh public
	./deploy/oracle/rehearse.sh release
