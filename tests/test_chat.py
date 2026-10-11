from unittest.mock import patch

import pytest

from application import application
from heatshift import chat, places, weather


@pytest.mark.parametrize("msg, hour", [
    ("I have to deliver at 2 pm", 14),
    ("at 14:30 near CP", 14),
    ("मुझे 3 बजे जाना है", 15),
    ("for 2 hours at 4 pm", 16),          # duration ignored, the time wins
    ("drink 500 ml at 9am", 9),
    ("leaving at 11", 11),
])
def test_parse_time(msg, hour):
    assert chat.parse_time(msg, default_hour=8) == (hour, True)


def test_parse_time_default_when_absent():
    assert chat.parse_time("Is it safe now?", default_hour=13) == (13, False)
    assert chat.parse_time("I will work 2 hours", default_hour=13) == (13, False)


@pytest.mark.parametrize("msg, expected", [
    ("my friend fainted", True),
    ("he is confused and hot", True),
    ("वो बेहोश हो गया", True),
    ("what are the benefits of ORS", False),   # 'fits' inside a word is not an emergency
    ("where can I drink water", False),
])
def test_emergency_detection(msg, expected):
    assert chat.is_emergency(msg) is expected


@pytest.mark.parametrize("msg, ui, expected", [
    ("mujhe english samjh nhi aati hindi mein bolo", "en", "hi"),   # Hinglish -> Hindi
    ("agar main ye jagah ka naam location mein daalu", "en", "hi"),
    ("मुझे पानी कहाँ मिलेगा?", "en", "hi"),                          # Devanagari -> Hindi
    ("Where can I drink water?", "en", "en"),
    ("Where can I drink water?", "hi", "hi"),                         # keeps the page language
    ("Is it safe at 2 pm in Delhi?", "en", "en"),
])
def test_reply_language(msg, ui, expected):
    assert chat.reply_language(msg, ui) == expected


def test_clean_strips_reasoning_tags():
    assert chat.clean("<thinking>plan</thinking>\nDrink water.") == "Drink water."


def test_rate_limit_per_ip():
    chat._hits.clear()
    for _ in range(chat.RATE_LIMIT):
        chat.check_rate("1.2.3.4", now=1000)
    with pytest.raises(chat.RateLimited):
        chat.check_rate("1.2.3.4", now=1001)
    chat.check_rate("5.6.7.8", now=1001)            # other users unaffected
    chat.check_rate("1.2.3.4", now=1000 + chat.RATE_WINDOW_S + 1)  # window slides


# ---- endpoint ----

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    monkeypatch.setenv("USE_BEDROCK", "1")
    weather._cache.clear()
    places._cache.clear()
    chat._hits.clear()
    with patch.object(weather, "_fetch", side_effect=weather.requests.ConnectionError("offline")), \
         patch.object(places.requests, "post", side_effect=places.requests.ConnectionError("offline")):
        yield application.test_client()


def ask(client, message, lang="en", **extra):
    body = {"message": message, "role": "rider", "city": "delhi", "lang": lang, "date": "2024-06-18", **extra}
    return client.post("/api/chat", json=body)


def test_bedrock_failure_falls_back_to_trip_checklist(client):
    with patch.object(chat, "_model_answer", side_effect=RuntimeError("AccessDeniedException")):
        r = ask(client, "I have to deliver at 2 pm, what do I do?")
    body = r.get_json()
    assert r.status_code == 200
    assert body["message_source"] == "template"
    assert body["fallback_reason"] == "RuntimeError"
    assert body["answer"].startswith("14:00–15:00")
    assert "108" in body["answer"]                 # danger -> stop signs included
    assert "charset=utf-8" in r.headers["Content-Type"]


def test_bedrock_timeout_falls_back(client, monkeypatch):
    monkeypatch.setattr(chat, "CHAT_TIMEOUT_S", 0.2)
    import time

    def slow(*a):
        time.sleep(1)
        return "late"

    with patch.object(chat, "_model_answer", side_effect=slow):
        body = ask(client, "is it safe now?").get_json()
    assert body["message_source"] == "template" and body["fallback_reason"] == "timeout"


def test_hindi_fallback_is_hindi(client):
    with patch.object(chat, "_model_answer", side_effect=RuntimeError("down")):
        body = ask(client, "मुझे 3 बजे जाना है", lang="hi").get_json()
    assert "महसूस तापमान" in body["answer"]


def test_hinglish_on_english_page_gets_hindi_answer(client):
    with patch.object(chat, "_model_answer", side_effect=RuntimeError("down")):
        body = ask(client, "mujhe 2 baje jana hai kya karu", lang="en").get_json()
    assert "महसूस तापमान" in body["answer"]


def test_water_question_fallback_lists_nearby_places(client):
    with patch.object(chat, "_model_answer", side_effect=RuntimeError("down")):
        body = ask(client, "Where can I drink water?", lat=28.6315, lon=77.2167).get_json()
    assert "Nearby:" in body["answer"]


def test_bedrock_answer_is_returned_with_source(client):
    with patch.object(chat, "_model_answer", return_value="Go at 17:00 instead. Drink water every 20 minutes."):
        body = ask(client, "I have to go at 2 pm").get_json()
    assert body["message_source"] == "bedrock:amazon.nova-lite-v1:0"
    assert body["answer"].startswith("Go at 17:00")


def test_non_hindi_model_reply_rejected_for_hindi(client):
    with patch.object(chat, "_model_answer", return_value="English only reply"):
        body = ask(client, "पानी कहाँ मिलेगा?", lang="hi").get_json()
    assert body["message_source"] == "template"


def test_emergency_skips_the_model(client):
    with patch.object(chat, "_model_answer") as model:
        body = ask(client, "my friend fainted and is not sweating").get_json()
    model.assert_not_called()
    assert body["emergency"] is True and "108" in body["answer"] and "112" in body["answer"]


def test_bedrock_disabled_uses_template(client, monkeypatch):
    monkeypatch.setenv("USE_BEDROCK", "0")
    with patch.object(chat, "_model_answer") as model:
        body = ask(client, "is it safe at 1 pm?").get_json()
    model.assert_not_called()
    assert body["message_source"] == "template"


@pytest.mark.parametrize("message, status", [("", 400), ("x" * 501, 400)])
def test_message_validation(client, message, status):
    assert ask(client, message).status_code == status


def test_rate_limited_endpoint(client):
    with patch.object(chat, "_model_answer", return_value="ok"):
        codes = [ask(client, "safe now?").status_code for _ in range(chat.RATE_LIMIT + 1)]
    assert codes[:-1] == [200] * chat.RATE_LIMIT and codes[-1] == 429
