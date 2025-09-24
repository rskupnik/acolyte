# ---- Base versions
ARG PYTHON_VERSION=3.13

# ---- Builder: create virtualenv and install deps
FROM python:${PYTHON_VERSION}-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# System deps for building wheels (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create venv
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Upgrade pip and install deps from pinned requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Build and wheel the app (no network needed later)
COPY pyproject.toml ./
COPY acolyte ./acolyte
RUN pip install --no-cache-dir build \
 && python -m build --wheel --outdir /dist

# ---- Runtime: copy only what we need
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app

# Security: run as non-root
RUN useradd -m appuser

# Copy venv site-packages and app wheel; install wheel offline
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /dist /dist
RUN pip install --no-cache-dir --no-index --find-links=/dist acolyte

# Drop privileges and set defaults
USER appuser
EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info UVICORN_WORKERS=1
CMD ["acolyte"]
