"""Heat-safety chat assistant: a Strands agent on Amazon Bedrock that answers from HeatShift's own tools.

The agent can only see numbers through three tools (get_plan, get_trip, find_places) that call our
deterministic code, and the system prompt forbids inventing temperatures. Every failure path returns
a deterministic answer built from the safe-trip checklist, so the chat never breaks.
"""
import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from .advice import config as bedrock_config
from .trip import STOP_SIGNS, plan_trip

log = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 500
MAX_ANSWER_CHARS = 1200
CHAT_TIMEOUT_S = 15
RATE_LIMIT = 10          # messages
RATE_WINDOW_S = 60       # per minute, per IP (kept in memory only)

_executor = ThreadPoolExecutor(max_workers=4)
_hits = defaultdict(deque)
_hits_lock = threading.Lock()

EMERGENCY_WORDS = (
    "faint", "fainted", "unconscious", "passed out", "collapse", "confus", "seizure", "fits", "fitting",
    "not sweating", "no sweat", "stopped sweating", "hot dry skin", "not responding",
    "बेहोश", "होश नहीं", "दौरे", "दौरा", "उलझन", "पसीना बंद", "गिर गया", "गिर गई",
)
WATER_WORDS = ("water", "drink", "shade", "rest", "sit", "ors", "पानी", "छाँव", "छांव", "आराम", "बैठ")
NOW_WORDS = ("now", "right now", "currently", "अभी", "इस समय")


class RateLimited(Exception):
    pass


def check_rate(ip, now=None):
    """Sliding-window limit per client IP. Nothing is persisted."""
    now = now or time.time()
    with _hits_lock:
        q = _hits[ip]
        while q and q[0] <= now - RATE_WINDOW_S:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            raise RateLimited()
        q.append(now)


def is_emergency(message):
    m = message.lower()
    for w in EMERGENCY_WORDS:
        if w.isascii():
            if re.search(r"\b" + re.escape(w), m):   # word start, so "benefits" is not "fits"
                return True
        elif w in m:
            return True
    return False


_TIME_RE = re.compile(r"(?<![\d.])(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|बजे)?(?!\s*(?:hours?|hrs?|mins?|minutes?|ml|km|घंटे|घंटा|मिनट))",
                      re.IGNORECASE)


def parse_time(message, default_hour):
    """Find a time like '2 pm', '14:00', '2 बजे' in the message. Returns (hour, found).
    Times with am/pm/बजे or hh:mm win over bare numbers; durations like '2 hours' are ignored."""
    candidates = []
    for hit in _TIME_RE.finditer(message.lower()):
        hour = int(hit.group(1))
        if hour > 23:
            continue
        suffix = (hit.group(3) or "").replace(".", "")
        strong = bool(suffix or hit.group(2))
        candidates.append((0 if strong else 1, hit.start(), hour, suffix))
    if not candidates:
        return default_hour, False
    _, _, hour, suffix = min(candidates)
    if suffix == "pm" and hour < 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif suffix in ("", "बजे") and 1 <= hour <= 7:
        hour += 12  # "2 बजे" / "at 3" during a work day means afternoon
    return hour, True


# Common Hindi words written in Latin letters (Hinglish). Two or more => the user wants Hindi.
HINGLISH_WORDS = {
    "mujhe", "mujhko", "main", "mein", "hai", "hain", "kya", "kaise", "kahan", "kahaan", "kab", "nahi", "nhi", "nahin",
    "bolo", "batao", "bataiye", "karna", "karu", "karun", "jana", "jaana", "jau", "jaun", "paani", "pani", "garmi",
    "dhoop", "chhaon", "chaon", "abhi", "aaj", "kal", "baje", "samajh", "samjh", "aati", "aata", "hindi", "mera",
    "meri", "yeh", "ye", "woh", "wo", "toh", "aur", "lekin", "kuch", "sakta", "sakti", "chahiye", "jagah", "daalu",
}


def reply_language(message, ui_lang):
    """Answer in the language the worker actually writes: Devanagari or Hinglish -> Hindi."""
    if any("ऀ" <= ch <= "ॿ" for ch in message):
        return "hi"
    words = re.findall(r"[a-z]+", message.lower())
    if sum(1 for w in words if w in HINGLISH_WORDS) >= 2:
        return "hi"
    return ui_lang


def emergency_answer(lang):
    s = STOP_SIGNS[lang]
    return f"{s['emergency_title']}.\n{s['emergency_do']}"


def _level_word(level, lang):
    words = {
        "en": {"safe": "Safe", "caution": "Caution", "danger": "Danger", "extreme": "Extreme danger"},
        "hi": {"safe": "सुरक्षित", "caution": "सावधान", "danger": "खतरा", "extreme": "अत्यधिक खतरा"},
    }
    return words[lang][level]


def template_answer(ctx, message, places_fn=None):
    """Deterministic answer: the trip checklist for the time in the message (or now)."""
    lang = ctx["lang"]
    hour, _ = parse_time(message, ctx["now_hour"])
    trip = plan_trip(ctx["rows"], ctx["role"], lang, hour, 1, earliest=ctx["earliest"])
    if lang == "hi":
        lines = [f"{trip['start']}–{trip['end']}: {_level_word(trip['risk_level'], lang)}, "
                 f"महसूस तापमान {round(trip['max_feels_c'])}°C तक।"]
    else:
        lines = [f"{trip['start']}–{trip['end']}: {_level_word(trip['risk_level'], lang)}, "
                 f"feels up to {round(trip['max_feels_c'])}°C."]
    if trip["alternative"]:
        lines.append(trip["alternative"]["text"])
    lines += ["- " + item for item in trip["checklist"][:4]]
    if places_fn and any(w in message.lower() for w in WATER_WORDS):
        spots = places_fn()
        if spots:
            head = "पास में:" if lang == "hi" else "Nearby:"
            lines.append(head + " " + "; ".join(spots[:3]))
    if trip["show_stop_signs_prominently"]:
        s = trip["stop_signs"]
        lines.append(f"{s['warning_title']}: {s['warning']} {s['emergency_title']}.")
    return "\n".join(lines), trip


SYSTEM_PROMPT = """You are HeatShift's heat-safety assistant for informal outdoor workers in India \
(street vendors, delivery riders, construction workers).

Scope: only heat safety at work: when to work or rest, going out in heat, water, shade, heat illness \
warning signs, and how to use this app. For anything else, reply in one short sentence that you can only \
help with heat safety at work.

Facts: ALWAYS call a tool before giving any number. Use get_plan for the day, get_trip whenever the user \
mentions a time (or "now"), find_places when they ask about water, shade or rest nearby. Use ONLY numbers, \
times and places returned by the tools. Never invent temperatures, times, places or distances.

Language: reply in {language}, whatever language the question is in. Never refuse because of language; \
if the user asks for Hindi or English, simply answer in it.

Each message is answered on its own: never ask the user a follow-up question. If something is missing \
(like their exact location), answer with what the tools give (find_places uses their saved location or the \
city centre). You cannot search for a place by its name; if asked, say to use the Nearby page and open \
"Open in Maps" there.

Style: at most 6 short lines, plain everyday words, concrete steps. Mention the safer \
alternative time if the tool gives one. Use at most 4 checklist steps. When listing places, give each \
place's name, what it is and the walking time. If the risk level is danger or extreme, end with this line exactly:
{stop_line}

Safety: no medical diagnosis, no medicine names or doses. If the user mentions confusion, fainting, hot dry \
skin, no sweating or fits, tell them to call 108 or 112 immediately and move the person to shade.
No markdown headings or tables. Lines starting with "- " are fine."""


def _model_answer(message, ctx, tools_used, cfg):
    import boto3
    import botocore.config
    from strands import Agent, tool
    from strands.models import BedrockModel

    lang = ctx["lang"]

    @tool
    def get_plan() -> str:
        """Today's heat plan for this worker: level per hour, hours to avoid, best hours, rest and water rules."""
        tools_used.append("get_plan")
        s = ctx["summary"]
        hours = [{"hour": r["time"], "level": r["level"], "feels_c": round(r["heat_index_c"])}
                 for r in ctx["rows"] if 5 <= r["hour"] <= 21]
        return json.dumps({
            "date": ctx["date"], "mode": ctx["mode"], "role": ctx["role"], "city": ctx["city_name"],
            "worst_level": s["worst_level"], "hottest_time": s["peak_time"],
            "hottest_feels_c": round(s["peak_heat_index_c"]),
            "avoid": [f"{a:02d}:00-{b:02d}:00" for a, b in s["avoid_windows"]],
            "best": [f"{a:02d}:00-{b:02d}:00" for a, b in s["best_windows"]],
            "rest_minutes_per_hot_hour": s["max_rest_min"], "water_every_minutes": s["min_water_every_min"],
            "hours": hours,
        }, ensure_ascii=False)

    @tool
    def get_trip(start_hour: int, hours: float = 1.0) -> str:
        """Risk for going out at start_hour (0-23, 24h clock) for a number of hours, with a checklist,
        the nearest safer time today, and stop signs."""
        tools_used.append("get_trip")
        start = max(0, min(23, int(start_hour)))
        n = max(1, min(12, int(round(hours + 0.49))))
        t = plan_trip(ctx["rows"], ctx["role"], lang, start, n, earliest=ctx["earliest"])
        return json.dumps({
            "window": f"{t['start']}-{t['end']}", "risk_level": t["risk_level"],
            "max_feels_c": round(t["max_feels_c"]),
            "safer_alternative": t["alternative"]["text"] if t["alternative"] else None,
            # the 4 most important general steps + the job-specific one, to keep answers short
            "checklist": t["checklist"][:4] + t["checklist"][-1:] if len(t["checklist"]) > 5 else t["checklist"],
            "stop_signs": t["stop_signs"],
        }, ensure_ascii=False)

    @tool
    def find_places() -> str:
        """Nearest places to drink water, buy water/ORS, or sit in shade (from OpenStreetMap)."""
        tools_used.append("find_places")
        spots = ctx["places_fn"]() if ctx.get("places_fn") else []
        return json.dumps({"places": spots or [], "note": "Opening hours not verified."}, ensure_ascii=False)

    s = STOP_SIGNS[lang]
    stop_line = f"{s['warning_title']}: {s['warning']} {s['emergency_title']}."
    prompt = SYSTEM_PROMPT.format(language="Hindi (Devanagari script)" if lang == "hi" else "English",
                                  stop_line=stop_line)
    prompt += (f"\n\nContext: worker = {ctx['role']}, city = {ctx['city_name']}, date = {ctx['date']} "
               f"({ctx['mode']}), current hour = {ctx['now_hour']:02d}:00.")

    model = BedrockModel(
        model_id=cfg["model_id"],
        boto_session=boto3.Session(region_name=cfg["region"]),
        streaming=False, max_tokens=900, temperature=0.2,  # Devanagari needs many more tokens
        boto_client_config=botocore.config.Config(connect_timeout=3, read_timeout=CHAT_TIMEOUT_S,
                                                  retries={"max_attempts": 1}),
    )
    agent = Agent(model=model, system_prompt=prompt, tools=[get_plan, get_trip, find_places],
                  callback_handler=None, retry_strategy=None)
    return clean(str(agent(message)))


def clean(text):
    """Drop model reasoning tags (e.g. Nova's <thinking>) and extra blank lines."""
    text = re.sub(r"<thinking>.*?</thinking>", "", text or "", flags=re.S | re.I)
    text = re.sub(r"</?(response|answer)>", "", text, flags=re.I)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _valid(text, lang):
    if not text or len(text) > MAX_ANSWER_CHARS:
        return False
    if lang == "hi":
        return any("ऀ" <= ch <= "ॿ" for ch in text)
    return True


def answer(message, ctx):
    """ctx: lang, role, city_name, date, mode, rows, summary, now_hour, earliest, places_fn.
    Returns dict(answer, message_source, tools_used[, fallback_reason])."""
    lang = reply_language(message, ctx["lang"])
    ctx = {**ctx, "lang": lang}
    if is_emergency(message):
        return {"answer": emergency_answer(lang), "message_source": "template", "tools_used": [],
                "emergency": True}

    tools_used = []
    cfg = bedrock_config()
    reason = None
    if cfg["enabled"] and cfg["model_id"]:
        try:
            future = _executor.submit(_model_answer, message, ctx, tools_used, cfg)
            text = future.result(timeout=CHAT_TIMEOUT_S)
            if _valid(text, lang):
                return {"answer": text, "message_source": f"bedrock:{cfg['model_id']}", "tools_used": tools_used}
            reason = "invalid model output"
        except FutureTimeout:
            reason = "timeout"
        except Exception as e:  # noqa: BLE001 - the chat must never break
            reason = type(e).__name__
        log.warning("chat fell back to template (%s)", reason)
    else:
        reason = "bedrock disabled"

    text, _ = template_answer(ctx, message, ctx.get("places_fn"))
    return {"answer": text, "message_source": "template", "tools_used": ["get_trip"], "fallback_reason": reason}
