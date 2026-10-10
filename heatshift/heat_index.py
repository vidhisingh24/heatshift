"""Heat index (NWS Rothfusz regression) and heat-stress levels.

Formula: NWS heat index algorithm (Rothfusz 1990, NWS Technical Attachment SR 90-23),
as published by the NWS Weather Prediction Center:
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml

Level cutoffs and the IMD air-temperature floor come from data/cities.json, so each
city can use locally defined thresholds.
"""
import math

LEVELS = ["safe", "caution", "danger", "extreme"]


def c_to_f(c):
    return c * 9 / 5 + 32


def f_to_c(f):
    return (f - 32) * 5 / 9


def heat_index_f(temp_f, rh):
    """Heat index in °F from air temperature (°F) and relative humidity (%)."""
    simple = 0.5 * (temp_f + 61.0 + (temp_f - 68.0) * 1.2 + rh * 0.094)
    if (simple + temp_f) / 2 < 80:
        return simple

    t, r = temp_f, rh
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * r
          - 0.22475541 * t * r - 0.00683783 * t * t
          - 0.05481717 * r * r + 0.00122874 * t * t * r
          + 0.00085282 * t * r * r - 0.00000199 * t * t * r * r)

    if r < 13 and 80 <= t <= 112:
        hi -= ((13 - r) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
    elif r > 85 and 80 <= t <= 87:
        hi += ((r - 85) / 10) * ((87 - t) / 5)
    return hi


def heat_index_c(temp_c, rh):
    """Heat index in °C from air temperature (°C) and relative humidity (%)."""
    return f_to_c(heat_index_f(c_to_f(temp_c), rh))


def level_for(hi_c, temp_c, city):
    """Heat-stress level: the higher of the heat-index level and the IMD air-temperature floor.

    city["hi_cutoffs_c"]: {"caution", "danger", "extreme"} heat-index lower bounds (°C).
    city["imd_floor_c"]: {"danger", "extreme"} air-temperature lower bounds (°C).
    """
    cut = city["hi_cutoffs_c"]
    if hi_c >= cut["extreme"]:
        hi_level = 3
    elif hi_c >= cut["danger"]:
        hi_level = 2
    elif hi_c >= cut["caution"]:
        hi_level = 1
    else:
        hi_level = 0

    floor = city["imd_floor_c"]
    if temp_c >= floor["extreme"]:
        floor_level = 3
    elif temp_c >= floor["danger"]:
        floor_level = 2
    else:
        floor_level = 0

    return LEVELS[max(hi_level, floor_level)]
