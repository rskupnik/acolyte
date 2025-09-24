from __future__ import annotations
import os

def env_str(key: str, default: str) -> str:
    return os.getenv(key, default)

def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

# Runtime config (override via env vars in k8s)
HOST = env_str("HOST", "0.0.0.0")
PORT = env_int("PORT", 8000)
LOG_LEVEL = env_str("LOG_LEVEL", "info")
WORKERS = env_int("UVICORN_WORKERS", 1)  # keep 1 per container; scale with replicas
