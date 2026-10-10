"""Template advice in English and Hindi. Always available; used when Bedrock is off or fails."""

TEXT = {
    "en": {
        "peak": "Hottest around {time}: feels like {hi}°C (air {temp}°C).",
        "avoid": {
            "construction": "Stop heavy work {windows}.",
            "rider": "Avoid deliveries {windows}.",
            "vendor": "Move your stall into shade or cover it {windows}.",
        },
        "rest": "In hot hours, rest {min} minutes every hour in shade.",
        "water": "Drink a glass of water every {min} minutes, even if you are not thirsty.",
        "best": "Best hours to work: {windows}.",
        "no_best": "No safe hours today. Cut outdoor work as much as you can.",
        "low": "Heat is low today. Normal work is fine; keep drinking water.",
        "window": "{a}:00–{b}:00",
        "join": " and ",
    },
    "hi": {
        "peak": "सबसे ज़्यादा गर्मी लगभग {time} बजे: महसूस तापमान {hi}°C (हवा {temp}°C)।",
        "avoid": {
            "construction": "{windows} भारी काम बंद रखें।",
            "rider": "{windows} डिलीवरी से बचें।",
            "vendor": "{windows} अपनी दुकान छाँव में रखें या ढक दें।",
        },
        "rest": "गर्म घंटों में हर घंटे {min} मिनट छाँव में आराम करें।",
        "water": "हर {min} मिनट में एक गिलास पानी पिएँ, प्यास न लगे तब भी।",
        "best": "काम के लिए बेहतर समय: {windows}।",
        "no_best": "आज कोई सुरक्षित समय नहीं है। बाहर का काम जितना हो सके कम करें।",
        "low": "आज गर्मी कम है। सामान्य काम ठीक है, पानी पीते रहें।",
        "window": "{a}:00–{b}:00",
        "join": " और ",
    },
}


def format_windows(windows, lang):
    t = TEXT[lang]
    return t["join"].join(t["window"].format(a=f"{a:02d}", b=f"{b:02d}") for a, b in windows)


def template_message(summary, role, lang):
    t = TEXT[lang]
    if summary["worst_level"] == "safe":
        return t["low"]

    parts = [t["peak"].format(time=summary["peak_time"], hi=round(summary["peak_heat_index_c"]),
                              temp=round(summary["peak_temp_c"]))]
    if summary["avoid_windows"]:
        parts.append(t["avoid"][role].format(windows=format_windows(summary["avoid_windows"], lang)))
    if summary["max_rest_min"]:
        parts.append(t["rest"].format(min=summary["max_rest_min"]))
    parts.append(t["water"].format(min=summary["min_water_every_min"]))
    if summary["best_windows"]:
        parts.append(t["best"].format(windows=format_windows(summary["best_windows"], lang)))
    else:
        parts.append(t["no_best"])
    return " ".join(parts)
