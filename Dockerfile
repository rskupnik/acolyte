ARG PYTHON_VERSION=3.13

# ---------- Builder
FROM python:${PYTHON_VERSION}-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# venv + deps
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Install Chromium *into* $PLAYWRIGHT_BROWSERS_PATH (in this stage)
RUN playwright install chromium

# Build your app wheel
COPY pyproject.toml ./
COPY acolyte ./acolyte
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /dist

# ---------- Runtime
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
RUN useradd -m appuser

# Copy venv, built wheel, and the browsers directory from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /dist /dist
COPY --from=builder /ms-playwright /ms-playwright

# Install system deps required by Chromium in the FINAL image
# (playwright install-deps wraps apt-get; do it here so runtime has the libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install-deps

# Install your app offline from /dist
RUN pip install --no-cache-dir --no-index --find-links=/dist acolyte

USER appuser
EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 LOG_LEVEL=info UVICORN_WORKERS=1
CMD ["acolyte"]
