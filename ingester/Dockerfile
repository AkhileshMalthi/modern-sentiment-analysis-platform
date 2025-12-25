FROM python:3.12-slim

WORKDIR /app

# Install uv from official image (faster than pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency metadata first for better caching
COPY pyproject.toml uv.lock ./

# Install locked dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy application code
COPY . ./

# Run the ingester script with uv (uses the venv)
CMD ["uv", "run", "python", "ingester.py"]