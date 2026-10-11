from unittest.mock import patch

import pytest

from application import application
from heatshift import weather


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)  # template text, no network calls
    weather._cache.clear()
    return application.test_client()


@pytest.fixture
def offline():
    """Force the bundled sample day so tests don't depend on the network."""
    with patch.object(weather, "_fetch", side_effect=weather.requests.ConnectionError("offline")):
        yield


def test_plan_returns_schedule_and_message(client, offline):
    r = client.get("/api/plan?city=delhi&role=rider&lang=en&date=2024-06-18")
    assert r.status_code == 200
    body = r.get_json()
    assert body["mode"] == "sample"
    assert len(body["hours"]) == 24
    assert body["message_source"] == "template"
    assert body["message"]
    assert "Open-Meteo" in body["attribution"]


def test_plan_exposes_thresholds_for_why_line(client, offline):
    body = client.get("/api/plan?date=2024-06-18").get_json()
    assert body["imd_floor_c"] == {"danger": 45.0, "extreme": 47.0}
    assert set(body["cutoffs_c"]) == {"caution", "danger", "extreme"}


def test_plan_in_hindi(client, offline):
    body = client.get("/api/plan?role=vendor&lang=hi&date=2024-06-18").get_json()
    assert body["role_name"] == "रेहड़ी-पटरी विक्रेता"
    assert "पानी" in body["message"]


PAGES = {"/": "home", "/setup": "setup", "/trip": "trip", "/nearby": "nearby", "/ask": "ask",
         "/plan": "plan", "/about": "about"}


@pytest.mark.parametrize("path, page", PAGES.items())
def test_every_page_renders_with_disclaimer_line(client, path, page):
    r = client.get(path)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert f'data-page="{page}"' in html
    assert 'data-t="disclaimer_short"' in html and 'href="/about"' in html
    assert "charset=utf-8" in r.headers["Content-Type"]


@pytest.mark.parametrize("path", ["/", "/trip", "/nearby", "/ask", "/plan", "/about"])
def test_pages_have_nav_with_active_item(client, path):
    html = client.get(path).get_data(as_text=True)
    for href in ("/trip", "/nearby", "/ask", "/plan"):
        assert f'href="{href}"' in html
    assert html.count('aria-current="page"') >= 1


def test_setup_page_has_no_nav(client):
    html = client.get("/setup").get_data(as_text=True)
    assert 'class="tab-bar"' not in html and 'id="setup-done"' in html


def test_each_page_loads_only_its_own_script(client):
    assert "trip.js" in client.get("/trip").get_data(as_text=True)
    assert "places.js" not in client.get("/trip").get_data(as_text=True)
    assert "chat.js" in client.get("/ask").get_data(as_text=True)
    assert "places.js" in client.get("/nearby").get_data(as_text=True)
    home = client.get("/").get_data(as_text=True)
    assert not any(s in home for s in ("trip.js", "places.js", "chat.js"))


def test_about_has_credits_and_full_disclaimer(client):
    html = client.get("/about").get_data(as_text=True)
    assert "Weather data by Open-Meteo.com" in html and "CC BY 4.0" in html
    assert "OpenStreetMap contributors" in html
    assert 'data-t="disclaimer"' in html


def test_plan_page_keeps_open_meteo_credit(client):
    assert "Weather data by Open-Meteo.com" in client.get("/plan").get_data(as_text=True)


def test_site_redirects_to_day_plan(client):
    r = client.get("/site")
    assert r.status_code == 301 and r.headers["Location"].endswith("/plan")


def test_json_declares_utf8(client, offline):
    r = client.get("/api/plan?lang=hi&date=2024-06-18")
    assert "charset=utf-8" in r.headers["Content-Type"]


@pytest.mark.parametrize("path", ["/", "/health", "/api/options", "/static/app.js", "/static/style.css"])
def test_every_response_declares_utf8(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "charset=utf-8" in r.headers["Content-Type"].lower()


def test_options_include_city_coordinates(client):
    delhi = client.get("/api/options").get_json()["cities"]["delhi"]
    assert 28 < delhi["lat"] < 29 and 76 < delhi["lon"] < 78


def test_options_lists_roles(client):
    body = client.get("/api/options").get_json()
    assert set(body["roles"]) == {"vendor", "rider", "construction"}


def test_every_city_has_replay_days_with_bundled_samples(client):
    cities = client.get("/api/options").get_json()["cities"]
    assert {"delhi", "ahmedabad"} <= set(cities)
    for key, c in cities.items():
        assert c["replay_days"], key
        first = c["replay_days"][0]["date"]
        assert (weather.SAMPLES_DIR / f"{key}_{first}.json").exists(), key


def test_second_city_offline_uses_its_own_sample(client, offline):
    body = client.get("/api/plan?city=ahmedabad&role=construction&lang=hi&date=2024-05-27").get_json()
    assert body["city_name"] == "अहमदाबाद"
    assert body["mode"] == "sample"
    assert body["date"] == "2024-05-27"


@pytest.mark.parametrize("query", [
    "city=atlantis", "role=pilot", "lang=fr", "date=2024-13-40", "date=2099-01-01",
])
def test_bad_input_is_400(client, query):
    assert client.get(f"/api/plan?{query}").status_code == 400
