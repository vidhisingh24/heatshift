import pytest

from heatshift import advice
from heatshift.cities import get_city
from heatshift.profiles import PROFILES

DELHI = get_city("delhi")
SUMMARY = {
    "peak_heat_index_c": 46.9,
    "peak_temp_c": 44.2,
    "peak_time": "13:00",
    "worst_level": "danger",
    "avoid_windows": [(12, 16)],
    "best_windows": [(5, 8), (18, 22)],
    "max_rest_min": 20,
    "min_water_every_min": 20,
    "danger_hours": 9,
}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    advice._cache.clear()
    advice._down_until = 0.0
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    monkeypatch.setenv("USE_BEDROCK", "1")


def get(lang="en", key=None):
    return advice.get_message(SUMMARY, PROFILES["rider"], DELHI, lang, key or ("delhi", "rider", lang, "2024-06-18", "replay"))


def test_no_model_id_uses_template(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID")
    called = []
    monkeypatch.setattr(advice, "_call_bedrock", lambda *a: called.append(1))
    msg, src = get()
    assert src == "template" and "12:00–16:00" in msg and not called


def test_use_bedrock_0_uses_template(monkeypatch):
    monkeypatch.setenv("USE_BEDROCK", "0")
    assert get()[1] == "template"


def test_bedrock_message_is_used_and_cached(monkeypatch):
    calls = []

    def fake(prompt, cfg):
        calls.append(prompt)
        return "Skip deliveries from 12 to 4. Rest 20 minutes every hour."

    monkeypatch.setattr(advice, "_call_bedrock", fake)
    msg, src = get()
    assert src == "bedrock:amazon.nova-lite-v1:0"
    assert msg.startswith("Skip deliveries")
    get()
    assert len(calls) == 1  # second call served from cache


def test_failure_falls_back_and_cools_down(monkeypatch):
    calls = []

    def boom(prompt, cfg):
        calls.append(1)
        raise RuntimeError("AccessDeniedException")

    monkeypatch.setattr(advice, "_call_bedrock", boom)
    msg, src = get()
    assert src == "template" and msg
    get(key=("delhi", "rider", "en", "2024-05-29", "replay"))
    assert len(calls) == 1  # cooldown: Bedrock not retried immediately


def test_hindi_reply_must_be_devanagari(monkeypatch):
    monkeypatch.setattr(advice, "_call_bedrock", lambda p, c: "Rest in the shade.")
    msg, src = get("hi")
    assert src == "template"
    assert "पानी" in msg


def test_overlong_reply_rejected(monkeypatch):
    monkeypatch.setattr(advice, "_call_bedrock", lambda p, c: "x" * (advice.MAX_CHARS + 1))
    assert get()[1] == "template"


def test_prompt_contains_only_computed_facts():
    p = advice.build_prompt(SUMMARY, PROFILES["vendor"], DELHI, "hi")
    assert "Hindi" in p
    assert "13:00" in p and "47°C" in p and "12:00–16:00" in p
    assert "shade" in p  # vendor action, not "stop"
