# HeatShift API

All responses are JSON with `charset=utf-8`. Errors return `{"error": "..."}` with status 400 (bad input), 429 (rate limit) or 503 (an upstream data source is unavailable).

Common parameters:

| Param | Values |
|---|---|
| `city` | `delhi` (default), `ahmedabad` |
| `role` | `vendor`, `rider` (default), `construction` |
| `lang` | `en` (default), `hi` |
| `date` | `YYYY-MM-DD`, optional. Empty means today's forecast. Past dates replay from the Open-Meteo archive. Up to 15 days ahead is allowed. |

## `GET /api/plan`

Example: `/api/plan?city=delhi&role=rider&lang=en&date=2024-06-18`

| Field | Meaning |
|---|---|
| `hours[]` | One item per hour: `time`, `hour`, `temp_c`, `rh`, `heat_index_c`, `level` (`safe` / `caution` / `danger` / `extreme`), `rest_min`, `water_every_min`, `avoid`, `avoid_action` (`stop` / `shade`) |
| `summary` | `peak_heat_index_c`, `peak_temp_c`, `peak_air_c`, `peak_rh`, `peak_time`, `worst_level`, `avoid_windows`, `best_windows`, `max_rest_min`, `min_water_every_min`, `danger_hours` |
| `message`, `message_source` | Daily advice; source is `bedrock:<model-id>` or `template` |
| `cutoffs_c`, `imd_floor_c` | Heat-index cutoffs and IMD air-temperature floors used for this city |
| `mode` | `forecast`, `recent`, `replay` or `sample` (bundled data when Open-Meteo is unreachable) |
| `data_source`, `data_fetched_at`, `attribution`, `generated_at` | Provenance |

## `GET /api/trip`

Example: `/api/trip?city=delhi&role=rider&lang=hi&date=2024-06-18&start=14:00&hours=2`

`start` takes `14`, `14:30` or `2pm`. `hours` takes 0.5–12 and is rounded up to whole hours.

| Field | Meaning |
|---|---|
| `risk_level`, `start`, `end`, `max_feels_c`, `max_air_c`, `window[]` | Risk for the trip window |
| `alternative` | Nearest safer window of the same length today (`start`, `end`, `shift_hours`, `level`, `max_feels_c`, `text`), or `null` |
| `checklist[]` | Steps for this job and level, in the requested language |
| `stop_signs` | `warning_title`, `warning`, `warning_do`, `emergency_title`, `emergency`, `emergency_do` |
| `show_stop_signs_prominently` | `true` at Danger or Extreme |
| `sources[]` | NCDC and NDMA links |

## `GET /api/places`

Example: `/api/places?lat=28.6304&lon=77.2177&radius=1000`

`radius` is clamped to 200–2000 m. Coordinates are never logged or stored.

| Field | Meaning |
|---|---|
| `groups.drink[]`, `groups.buy[]`, `groups.shade[]` | Up to 8 each, nearest first: `name`, `name_hi`, `kind`, `category`, `lat`, `lon`, `distance_m`, `walk_min`, `osm_url`, `map_url`, `geo_url` |
| `break[]` | "10-minute break": the 3 closest spots, the closest of each kind first |
| `source` | `openstreetmap` or `sample` (bundled central-Delhi OSM data) |
| `fallback_reason` | Present when Overpass failed |
| `attribution` | `© OpenStreetMap contributors (ODbL)` |

## `POST /api/chat`

Request:

```json
{"message": "I have to deliver at 2 pm", "role": "rider", "city": "delhi", "lang": "en",
 "date": "2024-06-18", "lat": 28.63, "lon": 77.21}
```

`lat` and `lon` are optional. `message` is at most 500 characters. The limit is 10 requests per minute per IP.

| Field | Meaning |
|---|---|
| `answer` | The reply, in the request's language |
| `message_source` | `bedrock:<model-id>` or `template` |
| `tools_used[]` | Any of `get_plan`, `get_trip`, `find_places` |
| `fallback_reason` | Present when the template answer was used |
| `emergency` | `true` when emergency words were detected; the model is skipped and the 108/112 steps are returned |

## Other endpoints

- `GET /api/options`: cities (names, coordinates, replay days) and roles.
- `GET /health`: returns `ok`.
