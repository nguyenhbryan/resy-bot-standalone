FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

FROM base AS deps

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
COPY app ./app
COPY resy_bot ./resy_bot

ENV PATH="/app/.venv/bin:${PATH}" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
