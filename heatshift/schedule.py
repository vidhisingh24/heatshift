"""Turn hourly weather into an occupation-specific work-and-rest schedule."""
from .heat_index import LEVELS, heat_index_c, level_for

WORK_DAY = (5, 21)  # hours shown as the working day: 05:00 to 21:59


def _rank(level):
    return LEVELS.index(level)


def build_schedule(hours, city, profile):
    """hours: [{"time": "HH:MM", "temp_c", "rh"}] -> (rows, summary)."""
    rows = []
    start, end = profile["avoid_window"]
    for h in hours:
        hour = int(h["time"][:2])
        hi = heat_index_c(h["temp_c"], h["rh"])
        level = level_for(hi, h["temp_c"], city)
        avoid = level == "extreme" or (
            start <= hour < end and _rank(level) >= _rank(profile["avoid_from_level"])
        )
        rows.append({
            "time": h["time"],
            "hour": hour,
            "temp_c": round(h["temp_c"], 1),
            "rh": round(h["rh"]),
            "heat_index_c": round(hi, 1),
            "level": level,
            "rest_min": profile["rest_min"][level],
            "water_every_min": profile["water_every_min"][level],
            "avoid": avoid,
            "avoid_action": profile["avoid_action"] if avoid else None,
        })
    return rows, summarize(rows)


def _windows(hours):
    """Group sorted hours into contiguous (start, end_exclusive) windows."""
    windows = []
    for h in hours:
        if windows and windows[-1][1] == h:
            windows[-1][1] = h + 1
        else:
            windows.append([h, h + 1])
    return [tuple(w) for w in windows]


def summarize(rows):
    day = [r for r in rows if WORK_DAY[0] <= r["hour"] <= WORK_DAY[1]]
    peak = max(rows, key=lambda r: r["heat_index_c"])
    worst = max(rows, key=lambda r: _rank(r["level"]))["level"]
    return {
        "peak_heat_index_c": peak["heat_index_c"],
        "peak_temp_c": max(r["temp_c"] for r in rows),
        "peak_air_c": peak["temp_c"],  # air temperature at the hottest feels-like hour
        "peak_rh": peak["rh"],
        "peak_time": peak["time"],
        "worst_level": worst,
        "avoid_windows": _windows([r["hour"] for r in day if r["avoid"]]),
        "best_windows": _windows([r["hour"] for r in day if r["level"] in ("safe", "caution") and not r["avoid"]]),
        "max_rest_min": max(r["rest_min"] for r in day) if day else 0,
        "min_water_every_min": min(r["water_every_min"] for r in day) if day else 60,
        "danger_hours": sum(1 for r in day if _rank(r["level"]) >= _rank("danger")),
    }
