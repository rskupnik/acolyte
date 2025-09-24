ARG PYTHON_VERSION=3.13

# ---------- Builder
FROM python:${PYTHON_VERSION}-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# venv
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Deps
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers & OS deps into image
# (installs Chromium only to keep image smaller)
RUN playwright install chromium \
 && playwright install-deps

# Build wheel for your app
COPY pyproject.toml ./
COPY acolyte ./acolyte
RUN pip install --no-cache-dir build \
 && python -m build --wheel --outdir /dist

# ---------- Runtime
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/opt/venv/

WORKDIR /app
RUN useradd -m appuser

# Copy runtime venv (includes playwright + browsers) and app wheel
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /dist /dist
RUN pip install --no-cache-dir --no-index --find-links=/dist acolyte

USER appuser
EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info UVICORN_WORKERS=1
CMD ["acolyte"]
