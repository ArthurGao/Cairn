# One image for the API and the worker (deploy/oracle/docker-compose.yml picks the command).
# Built natively on the arm64 demo VM; works on amd64 too.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
RUN useradd --create-home --uid 10001 cairn && mkdir -p /data && chown cairn /data

WORKDIR /app
# Dependencies first, so a code change does not reinstall them; uv's cache stays out of the image.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY config ./config
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-editable

USER cairn
ARG BUILD_SHA=""
ENV CAIRN_BUILD_SHA=$BUILD_SHA PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

EXPOSE 4700
CMD ["uvicorn", "cairn.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "4700"]
