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


def test_plan_in_hindi(client, offline):
    body = client.get("/api/plan?role=vendor&lang=hi&date=2024-06-18").get_json()
    assert body["role_name"] == "रेहड़ी-पटरी विक्रेता"
    assert "पानी" in body["message"]


def test_index_page_has_attribution_and_disclaimer(client):
    html = client.get("/").get_data(as_text=True)
    assert "Weather data by Open-Meteo.com" in html
    assert "CC BY 4.0" in html
    assert 'data-t="disclaimer"' in html


def test_json_declares_utf8(client, offline):
    r = client.get("/api/plan?lang=hi&date=2024-06-18")
    assert "charset=utf-8" in r.headers["Content-Type"]


def test_options_lists_roles(client):
    body = client.get("/api/options").get_json()
    assert set(body["roles"]) == {"vendor", "rider", "construction"}


@pytest.mark.parametrize("query", [
    "city=atlantis", "role=pilot", "lang=fr", "date=2024-13-40", "date=2099-01-01",
])
def test_bad_input_is_400(client, query):
    assert client.get(f"/api/plan?{query}").status_code == 400
