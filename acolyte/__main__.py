from __future__ import annotations
import uvicorn
from . import config

def main() -> None:
    uvicorn.run(
        "acolyte.api:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL,
        workers=config.WORKERS,
    )

if __name__ == "__main__":
    main()
