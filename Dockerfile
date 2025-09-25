ARG PYTHON_VERSION=3.13

############################
# Stage: deps
############################
FROM python:${PYTHON_VERSION}-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# System build deps for wheels (only if you need to build native deps)
# Keep minimal; this layer rarely changes.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create venv
RUN python -m venv /opt/venv

# Copy ONLY requirements to maximize cache hits
COPY requirements.txt .

# Install Python deps into the venv (with pip cache mount for speed)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers to a stable path & keep them in this layer
RUN playwright install chromium

############################
# Stage: build
############################
FROM python:${PYTHON_VERSION}-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /app

# Reuse the venv from deps for the build toolchain (no network re-install)
COPY --from=deps /opt/venv /opt/venv

# Copy only files needed to compute the wheel first to improve cache
COPY pyproject.toml ./

# Copy your source code last (this is what changes most often)
COPY acolyte ./acolyte

# Build the wheel; keep build tools out of final image
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install build && \
    python -m build --wheel --outdir /dist

############################
# Stage: runtime
############################
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
RUN useradd -m appuser

# Copy the venv so "playwright" exists in PATH
COPY --from=deps /opt/venv /opt/venv

# System libs required by Chromium in FINAL image
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install-deps

# Bring in the browsers dir
COPY --from=deps /ms-playwright /ms-playwright

COPY --from=build /dist /dist
RUN pip install --no-index --find-links=/dist acolyte

USER appuser
EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info UVICORN_WORKERS=1
CMD ["acolyte"]
