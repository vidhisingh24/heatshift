import json
from pathlib import Path

_CITIES_FILE = Path(__file__).resolve().parent.parent / "data" / "cities.json"

with open(_CITIES_FILE, encoding="utf-8") as f:
    CITIES = json.load(f)


def get_city(key):
    """Return the city config for `key` (e.g. "delhi"), or None if unknown."""
    return CITIES.get((key or "").strip().lower())
