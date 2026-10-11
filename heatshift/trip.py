"""'I can't avoid this time' safe-trip mode. Deterministic: no AI involved.

Guidance sources (also listed in the README):
- NCDC (MoHFW) Public Health Advisory, Extreme Heat/Heatwave: a cup of water every 20 minutes for
  workers, shade and rest breaks. https://ncdc.mohfw.gov.in/
- NDMA heat wave do's and don'ts: ORS and homemade drinks (lassi, lemon water, buttermilk), avoid
  alcohol/tea/coffee/carbonated drinks, light cotton clothes, damp cloth on head and neck,
  never leave anyone in a parked vehicle. https://ndma.gov.in/Natural-Hazards/Heat-Wave/Dos-Donts
- WIEGO, Working under heat: a practical guide for workers in Delhi (2025).
- Drinking 300-500 ml in the hour before heat exposure is general occupational / sports-medicine
  guidance (pre-hydration), not from the Indian advisories.
"""
import math

from .heat_index import LEVELS


def _rank(level):
    return LEVELS.index(level)


# (min_level, English, Hindi)
BASE_ITEMS = [
    ("caution", "Drink 1–2 glasses (300–500 ml) of water in the hour before you leave.",
     "निकलने से पहले के एक घंटे में 1–2 गिलास (300–500 ml) पानी पिएँ।"),
    ("caution", "On the way, drink a glass of water every 15–20 minutes, even if you are not thirsty.",
     "रास्ते में हर 15–20 मिनट में एक गिलास पानी पिएँ, प्यास न लगे तब भी।"),
    ("caution", "Good drinks: ORS, nimbu pani, chaas, coconut water. Avoid tea, coffee, cola, energy drinks and alcohol.",
     "अच्छे पेय: ORS, नींबू पानी, छाछ, नारियल पानी। चाय, कॉफ़ी, कोला, एनर्जी ड्रिंक और शराब से बचें।"),
    ("caution", "Wear light, loose cotton clothes. Keep a wet gamcha or cloth on your head and neck.",
     "हल्के, ढीले सूती कपड़े पहनें। सिर और गर्दन पर गीला गमछा या कपड़ा रखें।"),
    ("safe", "Carry a full water bottle.", "पानी की भरी बोतल साथ रखें।"),
    ("danger", "Plan shaded stops: rest 5–10 minutes in shade every 30–40 minutes.",
     "छाँव में रुकने की जगह पहले से सोचें: हर 30–40 मिनट में 5–10 मिनट छाँव में आराम करें।"),
    ("danger", "Split a long trip into short parts instead of doing it in one go.",
     "लंबे काम को छोटे हिस्सों में बाँटें, एक बार में सब न करें।"),
    ("danger", "Go slower than usual. Heat tires you faster.",
     "सामान्य से धीरे चलें। गर्मी में थकान जल्दी होती है।"),
    ("danger", "Never sit or rest inside a parked vehicle in the sun.",
     "धूप में खड़ी गाड़ी के अंदर कभी न बैठें, न आराम करें।"),
    ("danger", "Tell a friend or family member your route and when you will be back.",
     "किसी दोस्त या घरवाले को अपना रास्ता और लौटने का समय बताएँ।"),
    ("extreme", "Extreme heat: go only if it truly cannot wait, and keep the trip as short as possible.",
     "अत्यधिक गर्मी: तभी जाएँ जब बिल्कुल ज़रूरी हो, और काम जितना हो सके छोटा रखें।"),
]

ROLE_ITEMS = {
    "rider": [
        ("caution", "Use a ventilated helmet and keep a wet cloth under it.",
         "हवादार हेलमेट पहनें और उसके नीचे गीला कपड़ा रखें।"),
        ("danger", "Keep water in an insulated bag. Take breaks at shaded parking, petrol pumps or under flyovers.",
         "पानी इंसुलेटेड बैग में रखें। छायादार पार्किंग, पेट्रोल पंप या फ़्लाईओवर के नीचे रुककर आराम करें।"),
    ],
    "vendor": [
        ("caution", "Put a shade cover (umbrella or tarp) over your stall.",
         "दुकान के ऊपर छाँव लगाएँ (छाता या तिरपाल)।"),
        ("danger", "Don't stand on hot pavement for long; stand on a mat or in shade.",
         "गर्म फ़ुटपाथ पर ज़्यादा देर न खड़े रहें; चटाई पर या छाँव में खड़े हों।"),
    ],
    "construction": [
        ("caution", "Rotate heavy tasks with lighter ones and with co-workers.",
         "भारी काम को हल्के काम और साथियों के साथ बारी-बारी से करें।"),
        ("danger", "Rest in shade, not in the sun or a hot tin shed. Ask the supervisor for water and shade on site.",
         "धूप या गर्म टीन शेड में नहीं, छाँव में आराम करें। सुपरवाइज़र से साइट पर पानी और छाँव माँगें।"),
    ],
}

STOP_SIGNS = {
    "en": {
        "warning_title": "Stop if you feel",
        "warning": "Dizziness, headache, nausea, muscle cramps, very heavy sweating or a fast heartbeat.",
        "warning_do": "Stop work, get into shade, drink water or ORS, and cool your neck and head with water.",
        "emergency_title": "Emergency: call 108 (ambulance) or 112 now",
        "emergency": "Confusion, fainting, hot dry skin or no sweating, fits (seizures).",
        "emergency_do": "Move the person to shade and cool them with water and fanning while you wait. "
                        "Do not give drinks if they are not fully awake.",
    },
    "hi": {
        "warning_title": "ये महसूस हो तो रुकें",
        "warning": "चक्कर, सिरदर्द, जी मिचलाना, मांसपेशियों में ऐंठन, बहुत ज़्यादा पसीना या दिल की तेज़ धड़कन।",
        "warning_do": "काम रोकें, छाँव में जाएँ, पानी या ORS पिएँ, और गर्दन व सिर को पानी से ठंडा करें।",
        "emergency_title": "आपातकाल: तुरंत 108 (एम्बुलेंस) या 112 पर कॉल करें",
        "emergency": "उलझन, बेहोशी, गर्म सूखी त्वचा या पसीना बंद होना, दौरे पड़ना।",
        "emergency_do": "इंतज़ार करते हुए व्यक्ति को छाँव में ले जाएँ और पानी व हवा से ठंडा करें। "
                        "पूरी तरह होश में न हो तो कुछ पीने को न दें।",
    },
}

SOURCES = [
    {"name": "NCDC (MoHFW) Public Health Advisory: Extreme Heat/Heatwave",
     "url": "https://ncdc.mohfw.gov.in/uploads/pdf/5.%20Public%20Health%20Advisory_Extreme%20HeatHeatwave.pdf"},
    {"name": "NDMA: Heat wave do's and don'ts", "url": "https://ndma.gov.in/Natural-Hazards/Heat-Wave/Dos-Donts"},
]


def parse_start(value):
    """'14', '14:30', '2pm' -> hour 0-23. Raises ValueError."""
    s = str(value or "").strip().lower().replace(" ", "")
    if not s:
        raise ValueError("start is required")
    pm, am = s.endswith("pm"), s.endswith("am")
    s = s[:-2] if (pm or am) else s
    hour = int(s.split(":")[0])
    if pm and hour < 12:
        hour += 12
    if am and hour == 12:
        hour = 0
    if not 0 <= hour <= 23:
        raise ValueError("start hour must be 0-23")
    return hour


def parse_hours(value):
    try:
        h = float(value if value not in (None, "") else 1)
    except (TypeError, ValueError):
        raise ValueError("hours must be a number")
    if not 0 < h <= 12:
        raise ValueError("hours must be between 0 and 12")
    return max(1, math.ceil(h))


def _window(rows, start, n):
    win = [r for r in rows if start <= r["hour"] < start + n]
    worst = max(win, key=lambda r: (_rank(r["level"]), r["heat_index_c"]))
    return win, worst["level"], max(r["heat_index_c"] for r in win)


def checklist(level, role, lang):
    i = 1 if lang == "en" else 2
    items = BASE_ITEMS + ROLE_ITEMS.get(role, [])
    return [it[i] for it in items if _rank(level) >= _rank(it[0])]


def _alt_text(lang, shift, start, end, alt_hi, cur_hi):
    window = f"{start:02d}:00–{end:02d}:00"
    if lang == "hi":
        when = f"{abs(shift)} घंटे {'बाद' if shift > 0 else 'पहले'}"
        return f"अगर आप {when} जा सकें, तो {window} कम गर्म है: महसूस तापमान {round(alt_hi)}°C, अभी के {round(cur_hi)}°C के मुकाबले।"
    when = f"{abs(shift)} hour{'s' if abs(shift) != 1 else ''} {'later' if shift > 0 else 'earlier'}"
    return f"If you can go {when}, {window} is cooler: feels like {round(alt_hi)}°C vs {round(cur_hi)}°C."


def plan_trip(rows, role, lang, start, hours, earliest=0):
    """rows: schedule rows for the day. Returns the trip assessment dict."""
    n = min(hours, 24 - start)
    win, level, max_hi = _window(rows, start, n)

    # Nearest safer window of the same length, inside working hours if possible.
    best = None
    lo, hi_start = max(5, earliest), 22 - n
    for c in range(lo, hi_start + 1):
        if c == start:
            continue
        _, c_level, c_hi = _window(rows, c, n)
        better = _rank(c_level) < _rank(level) or (c_level == level and c_hi <= max_hi - 2)
        if better:
            key = (abs(c - start), _rank(c_level), c_hi)
            if best is None or key < best[0]:
                best = (key, c, c_level, c_hi)

    alternative = None
    if best:
        _, c, c_level, c_hi = best
        alternative = {
            "start": f"{c:02d}:00", "end": f"{c + n:02d}:00", "shift_hours": c - start,
            "level": c_level, "max_feels_c": round(c_hi, 1),
            "text": _alt_text(lang, c - start, c, c + n, c_hi, max_hi),
        }

    return {
        "start": f"{start:02d}:00",
        "end": f"{start + n:02d}:00",
        "hours": n,
        "risk_level": level,
        "max_feels_c": round(max_hi, 1),
        "max_air_c": round(max(r["temp_c"] for r in win), 1),
        "window": [{"time": r["time"], "level": r["level"], "heat_index_c": r["heat_index_c"]} for r in win],
        "alternative": alternative,
        "checklist": checklist(level, role, lang),
        "stop_signs": STOP_SIGNS[lang],
        "show_stop_signs_prominently": _rank(level) >= _rank("danger"),
        "sources": SOURCES,
    }
