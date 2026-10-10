from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from heatshift.cities import CITIES, get_city
from heatshift.messages import template_message
from heatshift.profiles import PROFILES, get_profile
from heatshift.schedule import build_schedule
from heatshift.weather import WeatherError, get_hourly, parse_date

# Elastic Beanstalk's Python platform looks for a WSGI callable named `application`.
application = Flask(__name__)
application.json.ensure_ascii = False  # keep Hindi readable in JSON

LANGS = ("en", "hi")
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"


def error(message, status=400):
    return jsonify({"error": message}), status


@application.get("/")
def index():
    return render_template("index.html")


@application.get("/health")
def health():
    return "ok"


@application.get("/api/options")
def options():
    return jsonify({
        "cities": {k: {"name_en": c["name_en"], "name_hi": c["name_hi"]} for k, c in CITIES.items()},
        "roles": {k: {"name_en": p["name_en"], "name_hi": p["name_hi"]} for k, p in PROFILES.items()},
        "langs": list(LANGS),
    })


@application.get("/api/plan")
def plan():
    city_key = request.args.get("city", "delhi").strip().lower()
    role = request.args.get("role", "rider").strip().lower()
    lang = request.args.get("lang", "en").strip().lower()

    city = get_city(city_key)
    if city is None:
        return error(f"unknown city '{city_key}'; choose one of: {', '.join(CITIES)}")
    profile = get_profile(role)
    if profile is None:
        return error(f"unknown role '{role}'; choose one of: {', '.join(PROFILES)}")
    if lang not in LANGS:
        return error(f"unknown lang '{lang}'; choose one of: {', '.join(LANGS)}")
    try:
        day = parse_date(request.args.get("date"))
        weather = get_hourly(city_key, city, day)
    except ValueError as e:
        return error(f"invalid date: {e}")
    except WeatherError as e:
        return error(str(e), 503)

    rows, summary = build_schedule(weather["hours"], city, profile)
    return jsonify({
        "city": city_key,
        "city_name": city[f"name_{lang}"],
        "role": role,
        "role_name": profile[f"name_{lang}"],
        "lang": lang,
        "date": weather["date"],
        "mode": weather["mode"],
        "hours": rows,
        "summary": summary,
        "message": template_message(summary, role, lang),
        "message_source": "template",
        "cutoffs_c": {k: v for k, v in city["hi_cutoffs_c"].items() if not k.startswith("_")},
        "data_source": weather["source"],
        "attribution": ATTRIBUTION,
        "data_fetched_at": weather["fetched_at"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


if __name__ == "__main__":
    application.run(debug=True)
