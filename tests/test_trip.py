from unittest.mock import patch

import pytest

from application import application
from heatshift import weather
from heatshift.cities import get_city
from heatshift.profiles import PROFILES
from heatshift.schedule import build_schedule
from heatshift.trip import checklist, parse_hours, parse_start, plan_trip

DELHI = get_city("delhi")
# Dry pre-monsoon day: cool morning, 46°C at 13-14h (IMD floor -> danger)
TEMPS = [30] * 8 + [34, 37, 40, 43, 45, 46, 46, 45, 43, 40, 37] + [33] * 5
ROWS, _ = build_schedule([{"time": f"{h:02d}:00", "temp_c": t, "rh": 10} for h, t in enumerate(TEMPS)],
                         DELHI, PROFILES["rider"])


@pytest.mark.parametrize("value, hour", [("14", 14), ("14:30", 14), ("2pm", 14), ("2 PM", 14), ("12am", 0), ("9am", 9)])
def test_parse_start(value, hour):
    assert parse_start(value) == hour


@pytest.mark.parametrize("value", ["", "25", "abc"])
def test_parse_start_rejects(value):
    with pytest.raises(ValueError):
        parse_start(value)


def test_parse_hours_rounds_up_and_limits():
    assert parse_hours("0.5") == 1
    assert parse_hours("2.2") == 3
    with pytest.raises(ValueError):
        parse_hours("0")
    with pytest.raises(ValueError):
        parse_hours("20")


def test_afternoon_trip_is_danger_with_safer_alternative():
    r = plan_trip(ROWS, "rider", "en", 13, 1)
    assert r["risk_level"] == "danger"
    assert r["start"] == "13:00" and r["end"] == "14:00"
    alt = r["alternative"]
    assert alt is not None
    assert alt["max_feels_c"] < r["max_feels_c"]
    assert "cooler" in alt["text"]
    assert r["show_stop_signs_prominently"] is True


def test_alternative_is_the_nearest_safer_window():
    r = plan_trip(ROWS, "rider", "en", 13, 1)
    # 10:00 (40°C) is danger too; the nearest lower-level hour is earlier or later, never 13:00 itself
    assert r["alternative"]["start"] != "13:00"
    shift = abs(r["alternative"]["shift_hours"])
    for c in range(5, 22):
        if abs(c - 13) < shift:
            nearer = plan_trip(ROWS, "rider", "en", c, 1)
            assert nearer["risk_level"] == "danger" and nearer["max_feels_c"] > r["max_feels_c"] - 2


def test_cool_morning_trip_is_safe_and_short_checklist():
    r = plan_trip(ROWS, "rider", "en", 6, 1)
    assert r["risk_level"] == "safe"
    assert r["checklist"] == ["Carry a full water bottle."]
    assert r["show_stop_signs_prominently"] is False


def test_checklist_grows_with_level_and_is_role_specific():
    caution = checklist("caution", "vendor", "en")
    danger = checklist("danger", "vendor", "en")
    assert len(danger) > len(caution)
    assert any("stall" in i for i in caution)
    assert any("helmet" in i for i in checklist("caution", "rider", "en"))
    assert not any("helmet" in i for i in checklist("danger", "construction", "en"))
    assert any("ORS" in i for i in danger)


def test_hindi_checklist_and_stop_signs():
    r = plan_trip(ROWS, "construction", "hi", 13, 2)
    assert any("पानी" in i for i in r["checklist"])
    assert "108" in r["stop_signs"]["emergency_title"]


def test_trip_never_suggests_past_hours():
    r = plan_trip(ROWS, "rider", "en", 13, 1, earliest=20)
    assert r["alternative"] is None or int(r["alternative"]["start"][:2]) >= 20


# ---- endpoint ----

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    weather._cache.clear()
    with patch.object(weather, "_fetch", side_effect=weather.requests.ConnectionError("offline")):
        yield application.test_client()


def test_trip_endpoint(client):
    r = client.get("/api/trip?city=delhi&role=rider&lang=hi&date=2024-06-18&start=14:00&hours=2")
    assert r.status_code == 200
    body = r.get_json()
    assert body["risk_level"] in ("danger", "extreme")
    assert body["start"] == "14:00" and body["end"] == "16:00"
    assert body["checklist"] and body["stop_signs"]["emergency"]
    assert "charset=utf-8" in r.headers["Content-Type"]


@pytest.mark.parametrize("query", ["start=", "start=30", "start=14&hours=99", "start=14&role=pilot"])
def test_trip_bad_input(client, query):
    assert client.get(f"/api/trip?date=2024-06-18&{query}").status_code == 400
