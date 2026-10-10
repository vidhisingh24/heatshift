"""Hourly temperature and humidity from Open-Meteo (no API key).

- No date / today / recent or upcoming dates: Open-Meteo forecast API.
- Dates older than ARCHIVE_LAG_DAYS: Open-Meteo historical archive (ERA5 reanalysis),
  used for "replay" of a real past heatwave day.
- If Open-Meteo fails: a bundled sample day from data/samples, clearly labelled.

Weather data by Open-Meteo.com (CC BY 4.0).
"""
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = "temperature_2m,relative_humidity_2m"
ARCHIVE_LAG_DAYS = 6       # archive data lags real time by about 5 days
MAX_FORECAST_DAYS = 15
TIMEOUT_S = 10
DEFAULT_REPLAY_DATE = "2024-06-18"

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

_cache = {}  # (city_key, date) -> (expires_at, result)


class WeatherError(Exception):
    pass


def city_today(city):
    tz = timezone(timedelta(minutes=city["utc_offset_minutes"]))
    return datetime.now(tz).date()


def _fetch(url, params):
    resp = requests.get(url, params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()["hourly"]


def _sample(city_key, day):
    path = SAMPLES_DIR / f"{city_key}_{day}.json"
    if not path.exists():
        path = SAMPLES_DIR / f"{city_key}_{DEFAULT_REPLAY_DATE}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["date"], data["hourly"]


def get_hourly(city_key, city, day=None):
    """Return {"date", "mode", "source", "fetched_at", "hours": [{"time", "temp_c", "rh"}]}.

    `day` is a datetime.date or None (today in the city's timezone).
    Raises ValueError for dates outside the supported range, WeatherError if no data at all.
    """
    today = city_today(city)
    day = day or today
    if day > today + timedelta(days=MAX_FORECAST_DAYS):
        raise ValueError(f"date must be at most {MAX_FORECAST_DAYS} days ahead")

    key = (city_key, day.isoformat())
    cached = _cache.get(key)
    if cached and cached[0] > time.time():
        return cached[1]

    use_archive = day <= today - timedelta(days=ARCHIVE_LAG_DAYS)
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "hourly": HOURLY_VARS,
        "timezone": city["tz"],
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    try:
        hourly = _fetch(ARCHIVE_URL if use_archive else FORECAST_URL, params)
        result_day = day.isoformat()
        if use_archive:
            mode, source = "replay", "Open-Meteo historical archive (ERA5 reanalysis)"
        else:
            mode, source = ("forecast" if day >= today else "recent"), "Open-Meteo forecast"
        ttl = 24 * 3600 if use_archive else 30 * 60
    except (requests.RequestException, KeyError, ValueError):
        sample = _sample(city_key, day.isoformat())
        if sample is None:
            raise WeatherError("weather data unavailable")
        result_day, hourly = sample
        mode, source = "sample", "Bundled sample day (Open-Meteo archive); live data unavailable"
        ttl = 5 * 60

    hours = [
        {"time": t[11:16], "temp_c": temp, "rh": rh}
        for t, temp, rh in zip(hourly["time"], hourly["temperature_2m"], hourly["relative_humidity_2m"])
        if temp is not None and rh is not None
    ]
    if not hours:
        raise WeatherError("no hourly data for this date")

    result = {
        "date": result_day,
        "mode": mode,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hours": hours,
    }
    _cache[key] = (time.time() + ttl, result)
    return result


def parse_date(value):
    """Parse YYYY-MM-DD, or return None for empty input. Raises ValueError if malformed."""
    if not value:
        return None
    return date.fromisoformat(value)
