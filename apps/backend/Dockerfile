FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.15.2-slim AS base
COPY --from=uv /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./

FROM base AS runtime
RUN uv sync --locked --no-dev
COPY app ./app
CMD ["uv", "run", "--locked", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--no-access-log"]

FROM base AS test
RUN uv sync --locked
COPY app ./app
COPY tests ./tests
CMD ["uv", "run", "--locked", "pytest"]
