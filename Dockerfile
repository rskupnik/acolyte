ARG PYTHON_VERSION=3.13

############################
# Stage: deps  (pip deps + browsers)
############################
FROM python:${PYTHON_VERSION}-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

# Only build tools needed to compile wheels (rare)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
COPY requirements.txt .

# Install Python deps (cached via BuildKit mount)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -U pip && pip install -r requirements.txt

# Download Chromium browsers ONCE here (lives outside code paths)
RUN playwright install chromium

############################
# Stage: runtime-base (OS libs only)
############################
FROM python:${PYTHON_VERSION}-slim AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

# Copy venv so the playwright CLI is available to run install-deps
COPY --from=deps /opt/venv /opt/venv

# Install OS libraries needed by Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && /opt/venv/bin/playwright install-deps

############################
# Stage: build (your code → wheel)
############################
FROM python:${PYTHON_VERSION}-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /app

# Reuse venv (tools) without hitting network again
COPY --from=deps /opt/venv /opt/venv

# Copy metadata first for better caching
COPY pyproject.toml ./
# Copy source last — this is what changes most often
COPY acolyte ./acolyte

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install build && python -m build -w -o /dist

############################
# Stage: runtime (final)
############################
FROM runtime-base AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

# Non-root user
RUN useradd -m appuser

# Bring browsers + wheel
COPY --from=deps /ms-playwright /ms-playwright
COPY --from=build /dist /dist

# Install app offline
RUN pip install --no-index --find-links=/dist acolyte

USER appuser
EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info UVICORN_WORKERS=1
CMD ["acolyte"]
