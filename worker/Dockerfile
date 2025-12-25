FROM python:3.12-slim

WORKDIR /app

# Install uv from official image (faster than pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files from worker subdirectory
COPY worker/pyproject.toml worker/uv.lock ./

# Install locked dependencies with cache mount and longer timeout
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=600 uv sync --frozen --no-dev

# Copy shared backend code (sentiment analyzer and models)
COPY backend/services/ ./backend/services/
COPY backend/models/ ./backend/models/
COPY backend/__init__.py ./backend/__init__.py

# Copy worker application code
COPY worker/*.py ./

# Set PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Set HuggingFace cache directory (will be mounted as volume)
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers

# Pre-download ML models during build to cache them
# This layer will be cached unless dependencies change
RUN --mount=type=cache,target=/root/.cache/huggingface \
    UV_HTTP_TIMEOUT=600 uv run python -c "\
import os; \
print('Downloading models to:', os.getenv('HF_HOME', 'default')); \
from transformers import pipeline; \
print('Downloading sentiment model...'); \
pipeline('text-classification', model='distilbert-base-uncased-finetuned-sst-2-english'); \
print('Downloading emotion model...'); \
pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base'); \
print('Models downloaded successfully')"

# Run the worker script with uv (uses the venv)
# Clean stale lock files before starting to prevent deadlocks
CMD ["sh", "-c", "rm -rf /root/.cache/huggingface/**/.locks && uv run python worker.py"]