"""Worker profiles: rest, water and hours-to-avoid rules per heat level.

Prototype values, loosely based on OSHA/ACGIH work-rest cycles (heavier work needs more rest)
and NIOSH guidance of about one cup of water every 15-20 minutes in heat. Not field-validated.
"""

PROFILES = {
    "construction": {
        "name_en": "Construction worker",
        "name_hi": "निर्माण मज़दूर",
        "workload": "heavy",
        # minutes of rest per hour, by level
        "rest_min": {"safe": 0, "caution": 15, "danger": 30, "extreme": 45},
        # drink water every N minutes, by level
        "water_every_min": {"safe": 60, "caution": 30, "danger": 15, "extreme": 15},
        # avoid outdoor work in this window when level is at least `avoid_from_level`
        "avoid_window": (12, 16),
        "avoid_from_level": "danger",
        "avoid_action": "stop",
    },
    "rider": {
        "name_en": "Delivery rider",
        "name_hi": "डिलीवरी राइडर",
        "workload": "moderate",
        "rest_min": {"safe": 0, "caution": 10, "danger": 20, "extreme": 40},
        "water_every_min": {"safe": 60, "caution": 30, "danger": 20, "extreme": 15},
        "avoid_window": (12, 16),
        "avoid_from_level": "danger",
        "avoid_action": "stop",
    },
    "vendor": {
        "name_en": "Street vendor",
        "name_hi": "रेहड़ी-पटरी विक्रेता",
        "workload": "light",
        "rest_min": {"safe": 0, "caution": 5, "danger": 15, "extreme": 30},
        "water_every_min": {"safe": 60, "caution": 30, "danger": 20, "extreme": 20},
        "avoid_window": (13, 16),
        "avoid_from_level": "danger",
        "avoid_action": "shade",  # vendors usually can't leave the stall: move to shade instead
    },
}


def get_profile(key):
    return PROFILES.get((key or "").strip().lower())
