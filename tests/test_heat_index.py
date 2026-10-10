import pytest

from heatshift.cities import get_city
from heatshift.heat_index import c_to_f, f_to_c, heat_index_c, heat_index_f, level_for

DELHI = get_city("delhi")


@pytest.mark.parametrize("temp_f, rh, chart", [
    (90, 50, 95),    # NWS Heat Index Chart values
    (90, 70, 106),
    (100, 40, 109),
    (96, 40, 101),
    (86, 40, 85),
])
def test_matches_nws_chart(temp_f, rh, chart):
    assert heat_index_f(temp_f, rh) == pytest.approx(chart, abs=1.0)


def test_mild_conditions_use_simple_formula():
    # (simple + T) / 2 < 80°F, so the Steadman simple formula is used
    assert heat_index_f(75, 40) == pytest.approx(0.5 * (75 + 61 + 7 * 1.2 + 40 * 0.094))


def test_low_humidity_adjustment_lowers_index():
    # RH < 13% between 80 and 112°F subtracts the NWS dry adjustment
    assert heat_index_f(100, 10) < heat_index_f(100, 13)


def test_celsius_wrapper_round_trips():
    assert f_to_c(c_to_f(37.0)) == pytest.approx(37.0)
    assert heat_index_c(32.22, 50) == pytest.approx(f_to_c(95), abs=0.6)


@pytest.mark.parametrize("hi_c, temp_c, expected", [
    (30.0, 30.0, "safe"),
    (35.0, 33.0, "caution"),
    (42.0, 38.0, "danger"),
    (55.0, 40.0, "extreme"),
])
def test_levels_from_heat_index(hi_c, temp_c, expected):
    assert level_for(hi_c, temp_c, DELHI) == expected


def test_imd_floor_45_forces_at_least_danger():
    # Dry heat: heat index can sit below the danger cutoff while air temp is 45°C
    assert level_for(38.0, 45.0, DELHI) == "danger"


def test_imd_floor_47_forces_extreme():
    assert level_for(40.0, 47.0, DELHI) == "extreme"


def test_floor_never_lowers_level():
    assert level_for(55.0, 45.0, DELHI) == "extreme"
