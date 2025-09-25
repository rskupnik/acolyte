from __future__ import annotations
from typing import Callable, Awaitable, Dict, Any
from .scripts import example, driver_license_check

Scraper = Callable[[dict], Awaitable[dict]]

REGISTRY: Dict[str, Scraper] = {
    "example": example.run,
    "driver_license_check": driver_license_check.run
}

def get_scraper(script_id: str) -> Scraper | None:
    return REGISTRY.get(script_id)
