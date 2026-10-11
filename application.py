import logging
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template, request

from heatshift.advice import get_message
from heatshift.cities import CITIES, get_city
from heatshift.profiles import PROFILES, get_profile
from heatshift.schedule import build_schedule
from heatshift.trip import parse_hours, parse_start, plan_trip
from heatshift.weather import WeatherError, city_today, get_hourly, parse_date


def city_hour(city):
    tz = timezone(timedelta(minutes=city["utc_offset_minutes"]))
    return datetime.now(tz).hour

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("heatshift")

# Elastic Beanstalk's Python platform looks for a WSGI callable named `application`.
application = Flask(__name__)
application.json.ensure_ascii = False  # keep Hindi readable in JSON
application.json.mimetype = "application/json; charset=utf-8"

LANGS = ("en", "hi")
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
_TEXT_TYPES = ("text/", "application/json", "application/javascript")


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@application.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify({"error": str(e)}), e.status


@application.after_request
def utf8_everywhere(resp):
    """Declare charset=utf-8 on every text response (Hindi must never be misread)."""
    ctype = resp.headers.get("Content-Type", "")
    if ctype.startswith(_TEXT_TYPES) and "charset" not in ctype.lower():
        resp.headers["Content-Type"] = ctype + "; charset=utf-8"
    return resp


def load_plan(city_key, role, lang, date_str):
    """Validate inputs, fetch weather and build the schedule. Raises ApiError on bad input."""
    city_key = (city_key or "delhi").strip().lower()
    role = (role or "rider").strip().lower()
    lang = (lang or "en").strip().lower()
    city = get_city(city_key)
    if city is None:
        raise ApiError(f"unknown city '{city_key}'; choose one of: {', '.join(CITIES)}")
    profile = get_profile(role)
    if profile is None:
        raise ApiError(f"unknown role '{role}'; choose one of: {', '.join(PROFILES)}")
    if lang not in LANGS:
        raise ApiError(f"unknown lang '{lang}'; choose one of: {', '.join(LANGS)}")
    try:
        day = parse_date(date_str)
        weather = get_hourly(city_key, city, day)
    except ValueError as e:
        raise ApiError(f"invalid date: {e}")
    except WeatherError as e:
        raise ApiError(str(e), 503)
    rows, summary = build_schedule(weather["hours"], city, profile)
    return {
        "city_key": city_key, "city": city, "role": role, "profile": profile, "lang": lang,
        "weather": weather, "rows": rows, "summary": summary,
    }


@application.get("/")
def index():
    return render_template("index.html")


@application.get("/health")
def health():
    return "ok"


@application.get("/api/options")
def options():
    return jsonify({
        "cities": {
            k: {
                "name_en": c["name_en"], "name_hi": c["name_hi"], "lat": c["lat"], "lon": c["lon"],
                "replay_days": c.get("replay_days", []),
            }
            for k, c in CITIES.items()
        },
        "roles": {k: {"name_en": p["name_en"], "name_hi": p["name_hi"]} for k, p in PROFILES.items()},
        "langs": list(LANGS),
    })


@application.get("/api/plan")
def plan():
    a = request.args
    p = load_plan(a.get("city"), a.get("role"), a.get("lang"), a.get("date"))
    city, profile, lang, weather, summary = p["city"], p["profile"], p["lang"], p["weather"], p["summary"]
    message, message_source = get_message(
        summary, profile, city, lang, (p["city_key"], p["role"], lang, weather["date"], weather["mode"]),
    )
    log.info("plan city=%s role=%s lang=%s date=%s mode=%s level=%s message_source=%s",
             p["city_key"], p["role"], lang, weather["date"], weather["mode"], summary["worst_level"], message_source)
    return jsonify({
        "city": p["city_key"],
        "city_name": city[f"name_{lang}"],
        "role": p["role"],
        "role_name": profile[f"name_{lang}"],
        "lang": lang,
        "date": weather["date"],
        "mode": weather["mode"],
        "hours": p["rows"],
        "summary": summary,
        "message": message,
        "message_source": message_source,
        "cutoffs_c": {k: v for k, v in city["hi_cutoffs_c"].items() if not k.startswith("_")},
        "imd_floor_c": {k: v for k, v in city["imd_floor_c"].items() if not k.startswith("_")},
        "data_source": weather["source"],
        "attribution": ATTRIBUTION,
        "data_fetched_at": weather["fetched_at"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def trip_for(p, start, hours):
    """Safe-trip assessment for a loaded plan. Past hours are not suggested on today's forecast."""
    weather = p["weather"]
    earliest = 0
    if weather["mode"] == "forecast" and weather["date"] == city_today(p["city"]).isoformat():
        earliest = city_hour(p["city"])
    return plan_trip(p["rows"], p["role"], p["lang"], start, hours, earliest=earliest)


@application.get("/api/trip")
def trip():
    a = request.args
    p = load_plan(a.get("city"), a.get("role"), a.get("lang"), a.get("date"))
    try:
        start = parse_start(a.get("start"))
        hours = parse_hours(a.get("hours"))
    except ValueError as e:
        raise ApiError(str(e))
    result = trip_for(p, start, hours)
    log.info("trip city=%s role=%s start=%s hours=%s risk=%s", p["city_key"], p["role"], start, hours, result["risk_level"])
    return jsonify({
        "city": p["city_key"], "role": p["role"], "lang": p["lang"],
        "date": p["weather"]["date"], "mode": p["weather"]["mode"], **result,
    })


if __name__ == "__main__":
    application.run(debug=True)
