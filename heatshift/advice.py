"""Advice message written by a Strands agent on Amazon Bedrock, with template fallback.

Configured by environment variables:
  BEDROCK_MODEL_ID   model or inference-profile ID (unset -> template only), e.g. amazon.nova-lite-v1:0
  BEDROCK_REGION     default ap-southeast-2
  USE_BEDROCK        "0" turns Bedrock off
  BEDROCK_TIMEOUT_S  default 8

Any failure (missing package, no access, timeout, odd output) returns the template message,
so the app never breaks because of the model.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from .messages import format_windows, template_message

log = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)
_cache = {}  # (city, role, lang, date, mode) -> (message, source)
_down_until = 0.0  # after a failure, skip Bedrock briefly so users don't wait on every request
COOLDOWN_S = 60
MAX_CHARS = 700

SYSTEM_PROMPT = """You write heat-safety advice for informal outdoor workers in India \
(street vendors, delivery riders, construction workers).
Rules:
- Use ONLY the facts given. Never invent temperatures, times or numbers.
- 3 to 4 short sentences, under 70 words. Plain words a worker with little schooling understands.
- Speak directly to the worker ("you"). Practical actions only: when to work, when to rest, water, shade.
- No headings, no lists, no emojis, no markdown, no greeting.
- Do not give medical diagnosis. You may say: if dizzy, confused or vomiting, stop, move to shade and call 108.
- Write in the requested language. For Hindi use simple everyday Hindi in Devanagari script."""


def config():
    return {
        "enabled": os.environ.get("USE_BEDROCK", "1") != "0",
        "model_id": os.environ.get("BEDROCK_MODEL_ID", "").strip(),
        "region": os.environ.get("BEDROCK_REGION", "ap-southeast-2").strip(),
        "timeout_s": float(os.environ.get("BEDROCK_TIMEOUT_S", "8")),
    }


def build_prompt(summary, profile, city, lang):
    facts = [
        f"Worker: {profile['name_en']} ({profile['workload']} physical work)",
        f"City: {city['name_en']}",
        f"Hottest time: {summary['peak_time']}, feels like {round(summary['peak_heat_index_c'])}°C "
        f"(air {round(summary['peak_temp_c'])}°C)",
        f"Worst heat level today: {summary['worst_level']}",
    ]
    if summary["avoid_windows"]:
        action = "move the stall into shade or cover it" if profile["avoid_action"] == "shade" else "stop outdoor work"
        facts.append(f"Hours to {action}: {format_windows(summary['avoid_windows'], 'en')}")
    if summary["max_rest_min"]:
        facts.append(f"Rest in shade during hot hours: {summary['max_rest_min']} minutes every hour")
    facts.append(f"Drink a glass of water every {summary['min_water_every_min']} minutes")
    if summary["best_windows"]:
        facts.append(f"Best hours to work: {format_windows(summary['best_windows'], 'en')}")
    else:
        facts.append("No safe working hours today")
    language = "Hindi (Devanagari script)" if lang == "hi" else "English"
    return f"Write today's advice in {language}.\nFacts:\n- " + "\n- ".join(facts)


def _call_bedrock(prompt, cfg):
    # Imported lazily so a missing or broken package only disables the AI message.
    import botocore.config
    from strands import Agent
    from strands.models import BedrockModel

    model = BedrockModel(
        model_id=cfg["model_id"],
        region_name=cfg["region"],
        streaming=False,
        max_tokens=300,
        temperature=0.3,
        boto_client_config=botocore.config.Config(
            connect_timeout=3, read_timeout=cfg["timeout_s"], retries={"max_attempts": 1},
        ),
    )
    # A fresh agent per request: no conversation history shared between users.
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None, retry_strategy=None)
    return str(agent(prompt)).strip()


def _looks_valid(text, lang):
    if not text or len(text) > MAX_CHARS:
        return False
    if lang == "hi":  # must actually be in Devanagari
        return any("ऀ" <= ch <= "ॿ" for ch in text)
    return True


def get_message(summary, profile, city, lang, cache_key):
    """Return (message, message_source). message_source is "bedrock:<model>" or "template"."""
    if cache_key in _cache:
        return _cache[cache_key]

    fallback = (template_message(summary, cache_key[1], lang), "template")
    cfg = config()
    if not (cfg["enabled"] and cfg["model_id"]):
        return fallback

    global _down_until
    if time.time() < _down_until:
        return fallback

    try:
        future = _executor.submit(_call_bedrock, build_prompt(summary, profile, city, lang), cfg)
        text = future.result(timeout=cfg["timeout_s"] + 2)
    except FutureTimeout:
        log.warning("Bedrock timed out after %ss; using template", cfg["timeout_s"])
        _down_until = time.time() + COOLDOWN_S
        return fallback
    except Exception as e:  # noqa: BLE001 - any model failure falls back to the template
        log.warning("Bedrock failed (%s: %s); using template", type(e).__name__, e)
        _down_until = time.time() + COOLDOWN_S
        return fallback

    if not _looks_valid(text, lang):
        log.warning("Bedrock output rejected (%d chars); using template", len(text or ""))
        return fallback

    result = (text, f"bedrock:{cfg['model_id']}")
    _cache[cache_key] = result
    return result
