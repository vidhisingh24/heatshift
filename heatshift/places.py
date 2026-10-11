"""Nearby water and rest spots from OpenStreetMap (Overpass API), proxied server-side.

Privacy: coordinates are used only for this lookup. They are never logged or stored
(the cache key is rounded to ~100 m and lives in memory for 10 minutes).
Data © OpenStreetMap contributors, ODbL.
"""
import json
import math
import time
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "HeatShift/1.0 (heat-safety prototype for outdoor workers; https://github.com/vidhisingh24/heatshift)"
TIMEOUT_S = 8
CACHE_TTL_S = 600
MAX_PER_CATEGORY = 8
WALK_M_PER_MIN = 80  # about 4.8 km/h
SAMPLE_FILE = Path(__file__).resolve().parent.parent / "data" / "samples" / "places_delhi.json"
SAMPLE_MAX_KM = 30   # use the Delhi sample only for points in or near Delhi

# OSM tag value -> (category, kind)
KINDS = {
    ("amenity", "drinking_water"): ("drink", "drinking_water"),
    ("amenity", "fountain"): ("drink", "fountain"),          # only kept when drinking_water=yes
    ("shop", "convenience"): ("buy", "shop"),
    ("shop", "kiosk"): ("buy", "kiosk"),
    ("shop", "supermarket"): ("buy", "supermarket"),
    ("amenity", "pharmacy"): ("buy", "pharmacy"),
    ("amenity", "cafe"): ("shade", "cafe"),
    ("amenity", "fast_food"): ("shade", "food"),
    ("amenity", "place_of_worship"): ("shade", "worship"),
    ("amenity", "community_centre"): ("shade", "community"),
    ("shop", "mall"): ("shade", "mall"),
    ("amenity", "bus_station"): ("shade", "bus"),
}
CATEGORIES = ("drink", "buy", "shade")

_cache = {}  # (lat3, lon3, radius) -> (expires_at, result)


class PlacesError(Exception):
    pass


def validate(lat, lon, radius):
    try:
        lat, lon = float(lat), float(lon)
        radius = int(float(radius)) if radius not in (None, "") else 1000
    except (TypeError, ValueError):
        raise ValueError("lat, lon and radius must be numbers")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("lat/lon out of range")
    return lat, lon, max(200, min(radius, 2000))


def build_query(lat, lon, radius):
    a = f"around:{radius},{lat:.5f},{lon:.5f}"
    return f"""[out:json][timeout:{TIMEOUT_S}];
(
  node({a})[amenity~"^(drinking_water|fountain|pharmacy|cafe|fast_food|place_of_worship|community_centre|bus_station)$"];
  node({a})[shop~"^(convenience|kiosk|supermarket|mall)$"];
  way({a})[amenity~"^(place_of_worship|community_centre|bus_station)$"];
  way({a})[shop~"^(mall|supermarket)$"];
);
out center 300;"""


def distance_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_elements(elements, lat, lon, radius):
    """Overpass elements -> places grouped by category, nearest first."""
    out = {c: [] for c in CATEGORIES}
    seen = set()
    for e in elements:
        tags = e.get("tags") or {}
        kind = None
        for key in ("amenity", "shop"):
            if (key, tags.get(key)) in KINDS:
                kind = KINDS[(key, tags[key])]
                break
        if not kind:
            continue
        if kind[1] == "fountain" and tags.get("drinking_water") != "yes":
            continue  # most fountains in OSM are decorative, not for drinking
        plat = e.get("lat", (e.get("center") or {}).get("lat"))
        plon = e.get("lon", (e.get("center") or {}).get("lon"))
        if plat is None or plon is None:
            continue
        d = distance_m(lat, lon, plat, plon)
        if d > radius:
            continue
        uid = (e.get("type", "node"), e.get("id"))
        if uid in seen:
            continue
        seen.add(uid)
        name = tags.get("name:en") or tags.get("name") or tags.get("name:hi") or ""
        out[kind[0]].append({
            "name": name,
            "name_hi": tags.get("name:hi") or "",
            "category": kind[0],
            "kind": kind[1],
            "lat": round(plat, 6),
            "lon": round(plon, 6),
            "distance_m": round(d),
            "walk_min": max(1, math.ceil(d / WALK_M_PER_MIN)),
            "osm_url": f"https://www.openstreetmap.org/{e.get('type', 'node')}/{e.get('id')}",
            "map_url": f"https://www.openstreetmap.org/?mlat={plat:.6f}&mlon={plon:.6f}#map=18/{plat:.6f}/{plon:.6f}",
            "geo_url": f"geo:{plat:.6f},{plon:.6f}?q={plat:.6f},{plon:.6f}",
        })
    for c in CATEGORIES:
        out[c].sort(key=lambda p: p["distance_m"])
        out[c] = out[c][:MAX_PER_CATEGORY]
    return out


def break_suggestions(groups, n=3):
    """A '10-minute break': the closest spot of each kind first, then the next closest overall."""
    picks = [groups[c][0] for c in CATEGORIES if groups[c]]
    picks.sort(key=lambda p: p["distance_m"])
    rest = sorted((p for c in CATEGORIES for p in groups[c][1:]), key=lambda p: p["distance_m"])
    return (picks + rest)[:n]


def _load_sample():
    with open(SAMPLE_FILE, encoding="utf-8") as f:
        return json.load(f)


def find_places(lat, lon, radius=1000):
    lat, lon, radius = validate(lat, lon, radius)
    key = (round(lat, 3), round(lon, 3), radius)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]

    source = "openstreetmap"
    try:
        resp = requests.post(OVERPASS_URL, data={"data": build_query(lat, lon, radius)},
                             headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except (requests.RequestException, ValueError):
        sample = _load_sample()
        c = sample["center"]
        if distance_m(lat, lon, c["lat"], c["lon"]) > SAMPLE_MAX_KM * 1000:
            raise PlacesError("place search unavailable right now")
        elements, source = sample["elements"], "sample"

    groups = parse_elements(elements, lat, lon, radius)
    result = {
        "source": source,
        "radius_m": radius,
        "groups": groups,
        "break": break_suggestions(groups),
        "count": sum(len(v) for v in groups.values()),
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "fetched_at": int(time.time()),
    }
    _cache[key] = (time.time() + (CACHE_TTL_S if source == "openstreetmap" else 60), result)
    return result
