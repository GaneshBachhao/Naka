# backend/Dockerfile
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"

# Dependencies first so this layer only rebuilds when pyproject.toml/uv.lock
# change, not on every source edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "naka.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
