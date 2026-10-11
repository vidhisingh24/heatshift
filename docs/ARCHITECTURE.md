# HeatShift architecture

One Flask app (`application.py`) on AWS Elastic Beanstalk serves the pages and a small JSON API ([API.md](API.md)). There are no accounts and no database.

## URLs

| URL | What it is |
|---|---|
| **https://d2rsnmdxkrj7b8.cloudfront.net** | Public link. Amazon CloudFront (distribution `E2W7JABBTC55GT`) provides HTTPS, which browsers require before they share a phone's location. |
| http://heatshift-env.eba-umys9bjc.ap-southeast-2.elasticbeanstalk.com | Fallback: the Elastic Beanstalk environment directly, over HTTP. Everything works here except "Use my location", which falls back to the city centre. |

CloudFront settings:
- **Origin:** the Beanstalk CNAME, HTTP only.
- **Viewers:** redirected to HTTPS.
- **Methods:** all allowed (POST is needed for `/api/chat`).
- **Policies:** managed cache policy **CachingDisabled**, managed origin request policy **AllViewer**.
- **Other:** compression on, price class 100.
- **Rate limit:** the client IP stays the first `X-Forwarded-For` entry, so the chat rate limit still applies per user.

## Pages

| Path | What it shows | Data it loads |
|---|---|---|
| `/setup` | First-visit job, city, location, language and optional work hours (saved in `localStorage`) | `/api/options` |
| `/` | Verdict ("Avoid … Best …"), 24-hour bar, rest and water rule, replay-day picker, links | `/api/plan` |
| `/trip` | "I can't avoid this time" safe-trip check | `/api/trip` on submit |
| `/nearby` | Water, ORS and shade near the user | `/api/places` on tap |
| `/ask` | AI chat | `/api/chat` on send |
| `/plan` | Day plan: shift blocks, chart, hour table, advice with Listen / WhatsApp / Print poster | `/api/plan` |
| `/about` | Problem, method, warning signs, sources and credits | none |

`/site` redirects to `/plan`. Every page shares `templates/base.html`: a header with EN/HI, a desktop top bar, a mobile bottom tab bar, and a one-line disclaimer.

## How it works, step by step

1. **Weather.** Hourly temperature and relative humidity come from [Open-Meteo](https://open-meteo.com/), which needs no API key.
   - Today and upcoming days use the forecast API.
   - Past days replay from the historical archive (ERA5 reanalysis). It is not heatwave season in October, so each city lists real 2024 heatwave days in `data/cities.json`:
     - Delhi: 18 Jun 2024 (humid) and 29 May 2024 (dry).
     - Ahmedabad: 27 May 2024 and 23 May 2024.
   - If Open-Meteo is unreachable, a bundled copy of the replay day is used and labelled on screen.
2. **Heat index.** Uses the NWS equation (Rothfusz regression, NWS Technical Attachment SR 90-23), including the NWS low- and high-humidity adjustments. It is computed in °F and returned in °C.
3. **Level.** The NWS Heat Index Chart bands, converted to °C and stored per city. IMD heatwave rules are applied on top as a floor: air ≥ 45°C means at least Danger, and ≥ 47°C means Extreme. The higher of the two levels wins.
4. **Schedule.** Each worker profile maps the level to rest minutes per hour, a water interval and hours to avoid (see below). Contiguous hours with the same instruction are grouped into shift blocks.
5. **Daily advice.** A Strands Agents agent on Amazon Bedrock writes 3–4 sentences from the computed numbers only. Any failure (no access, an 8 s timeout, or invalid output such as Hindi without Devanagari) returns template text in the same language. After a failure, Bedrock is skipped for 60 s.
6. **Safe trip (`/api/trip`).** Deterministic.
   - The risk is the worst level in the trip window.
   - The checklist is chosen by level and job, following NCDC and NDMA guidance, in English and Hindi.
   - The safer alternative is the nearest window of the same length with a lower level, or one that feels at least 2°C cooler. On today's forecast, hours that have already passed are never suggested.
   - It also returns the stop signs and the 108/112 emergency box.
7. **Places (`/api/places`).** A server-side proxy to the OpenStreetMap Overpass API.
   - Requests carry a descriptive User-Agent, have an 8 s timeout, and try a mirror second.
   - Results are cached in memory for 10 minutes on a ~100 m grid.
   - If Overpass is unavailable, a bundled OSM sample of central Delhi is used.
   - Places are grouped as:
     - **Drink water:** `drinking_water`, plus `fountain` only when `drinking_water=yes`.
     - **Buy water / ORS:** convenience, kiosk, supermarket, pharmacy.
     - **Sit in shade / AC:** cafe, fast food, place of worship, community centre, mall, bus station.
8. **Chat (`/api/chat`).** A Strands agent with three tools that call HeatShift's own code: `get_plan`, `get_trip(start_hour, hours)` and `find_places`.
   - The system prompt limits it to heat safety for outdoor workers, requires a tool call before any number, keeps answers to about 6 lines in the user's language, and forbids diagnosis or doses.
   - Emergency words skip the model and return the 108/112 steps at once.
   - Limits: 500 characters per message, 10 messages per minute per IP (held in memory only), and a 15 s timeout.
   - Any failure returns the deterministic trip checklist with `message_source="template"`.

## Worker profiles

These are prototype values, loosely based on OSHA/ACGIH work–rest cycles and NIOSH guidance on drinking water in heat. They have not been validated in the field. See `heatshift/profiles.py`.

| Profile | Rest min per hour (caution / danger / extreme) | Water every (danger) | Hours to avoid at Danger or above |
|---|---|---|---|
| Construction worker (heavy) | 15 / 30 / 45 | 15 min | 12:00–16:00, stop heavy work |
| Delivery rider (moderate) | 10 / 20 / 40 | 20 min | 12:00–16:00, no deliveries |
| Street vendor (light) | 5 / 15 / 30 | 20 min | 13:00–16:00, move into shade or cover the stall |

Any Extreme hour is marked "avoid" for every profile.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `BEDROCK_MODEL_ID` | *(unset → template only)* | e.g. `amazon.nova-lite-v1:0` |
| `BEDROCK_REGION` | `ap-southeast-2` | Bedrock region |
| `USE_BEDROCK` | `1` | `0` forces template text |
| `BEDROCK_TIMEOUT_S` | `8` | Time limit for the daily-advice call (chat uses 15 s) |

## Deploy

```powershell
aws login --region ap-southeast-2
.\deploy.ps1 -Label v20
```

`deploy.ps1`:
1. Zips the app files at the zip root.
2. Uploads the zip to S3 (`heatshift-deploy-…`).
3. Runs `create-application-version`.
4. Runs `update-environment` on `heatshift-env`.
5. Waits until the environment is Ready and running the new version.
6. Checks `/health`.

It stops at the first failing step. The environment runs Python 3.12 on Amazon Linux 2023 on a single t3.small instance, with the instance role `aws-elasticbeanstalk-ec2-role` (AWSElasticBeanstalkWebTier + AmazonBedrockFullAccess).

## Add a city

Add one entry to `data/cities.json`:
- name in English and Hindi
- `lat` and `lon`
- `tz` and `utc_offset_minutes`
- `hi_cutoffs_c` and `imd_floor_c`
- `replay_days`

Optionally, save an offline copy of the first replay day as `data/samples/<city>_<date>.json`. No code changes are needed; Ahmedabad was added this way.

## Project layout

```
application.py        Flask app: pages + /api/* (Beanstalk looks for `application`)
heatshift/            heat_index, weather, cities, profiles, schedule, messages, advice,
                      trip (safe-trip checklist), places (Overpass proxy), chat (Strands agent + tools)
data/cities.json      per-city location, thresholds and replay days
data/samples/         offline replay days + OSM sample for central Delhi
templates/            base.html + one template per page
static/               style.css, i18n.js (EN/HI), app.js (shared), trip.js, places.js, chat.js
tests/                pytest: heat index, schedule, API and pages, advice, trip, places (mocked Overpass), chat fallback
deploy.ps1            CLI redeploy to Elastic Beanstalk
docs/                 API, architecture, writeup, demo script, blog, screenshots
```
