from unittest.mock import MagicMock, patch

import pytest

from application import application
from heatshift import places

LAT, LON = 28.6315, 77.2167

OVERPASS = {"elements": [
    {"type": "node", "id": 1, "lat": 28.6320, "lon": 77.2167, "tags": {"amenity": "drinking_water"}},
    {"type": "node", "id": 2, "lat": 28.6400, "lon": 77.2167, "tags": {"amenity": "drinking_water", "name": "Far tap"}},
    {"type": "node", "id": 3, "lat": 28.6316, "lon": 77.2170, "tags": {"shop": "kiosk", "name": "Chai stall"}},
    {"type": "node", "id": 4, "lat": 28.6330, "lon": 77.2180, "tags": {"amenity": "pharmacy", "name": "Medicos", "name:hi": "मेडिकोस"}},
    {"type": "way", "id": 5, "center": {"lat": 28.6340, "lon": 77.2150}, "tags": {"amenity": "place_of_worship", "name": "Temple"}},
    {"type": "node", "id": 6, "lat": 28.6318, "lon": 77.2160, "tags": {"amenity": "fountain", "name": "Decorative"}},
    {"type": "node", "id": 7, "lat": 28.6319, "lon": 77.2161, "tags": {"amenity": "fountain", "drinking_water": "yes"}},
    {"type": "node", "id": 8, "lat": 28.6319, "lon": 77.2161, "tags": {"amenity": "bank"}},
    {"type": "node", "id": 9, "lat": 28.7500, "lon": 77.2167, "tags": {"amenity": "cafe", "name": "Too far"}},
]}


def test_parse_groups_sorts_and_filters():
    g = places.parse_elements(OVERPASS["elements"], LAT, LON, 1000)
    drink = g["drink"]
    assert [p["kind"] for p in drink] == ["drinking_water", "fountain", "drinking_water"]  # nearest first
    assert all(p["name"] != "Decorative" for p in drink)                   # decorative fountain dropped
    assert drink[0]["distance_m"] < drink[1]["distance_m"] < drink[2]["distance_m"]
    assert {p["kind"] for p in g["buy"]} == {"kiosk", "pharmacy"}
    assert g["shade"][0]["name"] == "Temple"                               # way uses its centre
    assert all(p["name"] != "Too far" for c in g.values() for p in c)      # outside radius
    assert not any(p["name"] == "bank" for c in g.values() for p in c)     # unknown tag ignored


def test_walk_minutes_and_links():
    p = places.parse_elements(OVERPASS["elements"], LAT, LON, 1000)["buy"][0]
    assert p["name"] == "Chai stall"
    assert p["walk_min"] >= 1
    assert p["osm_url"] == "https://www.openstreetmap.org/node/3"
    assert p["geo_url"].startswith("geo:28.6316")


def test_break_suggestions_pick_three_closest_with_variety():
    g = places.parse_elements(OVERPASS["elements"], LAT, LON, 1000)
    picks = places.break_suggestions(g)
    assert len(picks) == 3
    assert {p["category"] for p in picks} == {"drink", "buy", "shade"}


def test_query_has_all_requested_tags():
    q = places.build_query(LAT, LON, 1000)
    for tag in ("drinking_water", "fountain", "convenience", "kiosk", "supermarket", "pharmacy", "cafe",
                "fast_food", "place_of_worship", "community_centre", "mall", "bus_station"):
        assert tag in q


@pytest.mark.parametrize("args", [("x", 1, 1000), (91, 77, 1000), (28, 181, 1000)])
def test_validate_rejects(args):
    with pytest.raises(ValueError):
        places.validate(*args)


def test_validate_clamps_radius():
    assert places.validate(28, 77, 99999)[2] == 2000
    assert places.validate(28, 77, 10)[2] == 200


@pytest.fixture
def client():
    places._cache.clear()
    return application.test_client()


def test_endpoint_uses_overpass_with_user_agent_and_caches(client):
    resp = MagicMock()
    resp.json.return_value = OVERPASS
    resp.raise_for_status.return_value = None
    with patch.object(places.requests, "post", return_value=resp) as post:
        r1 = client.get("/api/places?lat=28.6312&lon=77.2167&radius=1000")
        r2 = client.get("/api/places?lat=28.6313&lon=77.2168&radius=1000")  # same ~100 m cell
    assert r1.status_code == 200 and r2.status_code == 200
    assert post.call_count == 1
    assert "HeatShift" in post.call_args.kwargs["headers"]["User-Agent"]
    assert post.call_args.kwargs["timeout"] == 8
    body = r1.get_json()
    assert body["source"] == "openstreetmap"
    assert "OpenStreetMap" in body["attribution"]


def test_endpoint_falls_back_to_bundled_delhi_sample(client):
    with patch.object(places.requests, "post", side_effect=places.requests.Timeout("slow")):
        r = client.get(f"/api/places?lat={LAT}&lon={LON}")
    body = r.get_json()
    assert r.status_code == 200
    assert body["source"] == "sample"
    assert body["groups"]["drink"]


def test_endpoint_outside_delhi_without_overpass_is_503(client):
    with patch.object(places.requests, "post", side_effect=places.requests.ConnectionError("down")):
        r = client.get("/api/places?lat=19.07&lon=72.87")
    assert r.status_code == 503


def test_endpoint_bad_input(client):
    assert client.get("/api/places?lat=abc&lon=1").status_code == 400
