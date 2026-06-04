"""In-memory loads store backed by a JSON file.

Loaded once at startup; the file is the source of truth for this POC (no DB).
The full `Load` (including the hidden `max_buy_rate`) stays server-side. Only
`search` returns the stripped `LoadPublic`; `get` returns the full record for
the pricing authority to read `max_buy_rate` without ever echoing it.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.models import Load, LoadPublic


@lru_cache
def _load_all() -> list[Load]:
    path = Path(get_settings().loads_file)
    if not path.exists():
        return []
    return [Load(**item) for item in json.loads(path.read_text())]


def get_load(load_id: str) -> Load | None:
    """Full internal record (includes max_buy_rate) — server-side use only."""
    return next((ld for ld in _load_all() if ld.load_id == load_id), None)


def search_loads(
    origin: str | None = None,
    destination: str | None = None,
    equipment_type: str | None = None,
) -> list[LoadPublic]:
    """Filter on whatever is provided. Case-insensitive substring on
    origin/destination; case-insensitive exact match on equipment_type.
    Returns stripped public loads (no max_buy_rate)."""

    def matches(ld: Load) -> bool:
        if origin and origin.lower() not in ld.origin.lower():
            return False
        if destination and destination.lower() not in ld.destination.lower():
            return False
        if equipment_type and equipment_type.lower() != ld.equipment_type.lower():
            return False
        return True

    return [ld.public() for ld in _load_all() if matches(ld)]
