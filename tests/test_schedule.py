import pytest

from heatshift.cities import get_city
from heatshift.profiles import PROFILES, get_profile
from heatshift.schedule import _windows, build_schedule

DELHI = get_city("delhi")


def hours_from(temps, rh=10):
    """24 hourly rows, one temperature per hour (default: dry pre-monsoon Delhi air)."""
    return [{"time": f"{h:02d}:00", "temp_c": t, "rh": rh} for h, t in enumerate(temps)]


# Cool night, hot afternoon peaking at 46°C (IMD heat wave floor -> danger)
HOT_DAY = hours_from([30] * 8 + [34, 37, 40, 43, 45, 46, 46, 45, 43, 40, 37] + [33] * 5)


def test_every_profile_has_rules_for_every_level():
    for p in PROFILES.values():
        for level in ("safe", "caution", "danger", "extreme"):
            assert level in p["rest_min"]
            assert level in p["water_every_min"]


def test_unknown_profile_is_none():
    assert get_profile("pilot") is None
    assert get_profile(" Rider ") is PROFILES["rider"]


def test_one_row_per_hour_with_expected_fields():
    rows, _ = build_schedule(HOT_DAY, DELHI, PROFILES["rider"])
    assert len(rows) == 24
    assert set(rows[0]) >= {"time", "temp_c", "rh", "heat_index_c", "level", "rest_min", "water_every_min", "avoid"}


def test_cool_morning_is_safe_with_no_rest():
    rows, _ = build_schedule(HOT_DAY, DELHI, PROFILES["construction"])
    assert rows[6]["level"] == "safe"
    assert rows[6]["rest_min"] == 0
    assert rows[6]["avoid"] is False


def test_afternoon_heatwave_hours_are_avoided_for_riders():
    rows, summary = build_schedule(HOT_DAY, DELHI, PROFILES["rider"])
    assert rows[13]["level"] == "danger"          # 46°C -> IMD floor
    assert rows[13]["avoid"] is True
    assert rows[13]["avoid_action"] == "stop"
    assert (12, 16) in summary["avoid_windows"]


def test_vendor_moves_to_shade_instead_of_stopping():
    rows, _ = build_schedule(HOT_DAY, DELHI, PROFILES["vendor"])
    assert rows[14]["avoid_action"] == "shade"
    assert rows[12]["avoid"] is False             # vendor window starts at 13:00


def test_heavier_work_gets_more_rest():
    c, _ = build_schedule(HOT_DAY, DELHI, PROFILES["construction"])
    r, _ = build_schedule(HOT_DAY, DELHI, PROFILES["rider"])
    v, _ = build_schedule(HOT_DAY, DELHI, PROFILES["vendor"])
    assert c[13]["rest_min"] > r[13]["rest_min"] > v[13]["rest_min"]


def test_extreme_is_avoided_at_any_hour():
    rows, summary = build_schedule(hours_from([48] * 24), DELHI, PROFILES["vendor"])
    assert all(r["level"] == "extreme" and r["avoid"] for r in rows)
    assert summary["best_windows"] == []


def test_summary_peak():
    _, summary = build_schedule(HOT_DAY, DELHI, PROFILES["rider"])
    assert summary["peak_temp_c"] == 46
    assert summary["peak_time"] in ("13:00", "14:00")
    assert summary["worst_level"] == "danger"
    assert summary["danger_hours"] >= 2


@pytest.mark.parametrize("hours, expected", [
    ([], []),
    ([5, 6, 7], [(5, 8)]),
    ([5, 6, 9, 10, 12], [(5, 7), (9, 11), (12, 13)]),
])
def test_windows(hours, expected):
    assert _windows(hours) == expected
