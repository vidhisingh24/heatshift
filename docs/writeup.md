# HeatShift: submission writeup

**Track:** Heat and Water · **Live:** http://heatshift-env.eba-umys9bjc.ap-southeast-2.elasticbeanstalk.com · **Repo:** https://github.com/vidhisingh24/heatshift

## The problem

India's heat action plans are built around warnings: a colour code and a temperature. The Centre for Policy Research reviewed 37 of these plans and found that only 10 set locally defined thresholds and only 2 assessed who is vulnerable (Pillai & Dalal, CPR, 2023).

The people most exposed are informal outdoor workers: street vendors, delivery riders and construction workers. They can't stay indoors, and most have no support at work. In a WIEGO survey of around 500 Delhi street vendors in 2025, 89% had no access to free clean drinking water while working ([Question of Cities](https://questionofcities.org/mapping-heat-stress-shows-delhi-street-vendors-precarity/)).

A warning that says "44°C" leaves the decision to them. Should they take the 1 PM delivery? How long should they rest? How often should they drink water?

## Who it's for

- **Ravi, delivery rider:** paid per order, so he rides through the afternoon. He needs to know which hours to skip and how to space his breaks.
- **Sunita, street vendor:** can't leave her stall. She needs to know when to move into shade or cover the stall, and how often to drink water she has to buy.
- **Imran, construction worker:** does heavy work on site. He needs longer rest cycles, and a clear "stop" window his supervisor can see.

## What I built

HeatShift is a mobile-first web app. You pick your city, your work and your language, and get:

- A **heat level for the day** (Safe, Caution, Danger, Extreme danger) and the hottest hour.
- **Three numbers:** hours to stop work (or move into shade), rest minutes per hot hour, and a water reminder interval.
- **A shift plan** that groups the working day into blocks (work, work with breaks, stop), plus an interactive temperature chart and an hour-by-hour table.
- **Print or save as PDF**, giving a one-page notice for a site supervisor or market board.
- **Know the signs:** heat exhaustion vs. heat stroke, and when to call 108.
- **A short advice message in English or Hindi**, with a Listen button that reads it aloud and a **Share on WhatsApp** button for passing the plan to co-workers.
- **"I can't avoid this time" safe-trip mode.** "I have to go out at 14:00 for 2 hours" returns the risk for that window, a checklist for the job (NCDC/NDMA guidance), the nearest cooler time ("go 3 hours later: feels like 44°C instead of 46°C"), and a red stop-signs box with 108/112 call buttons.
- **Find water and shade near me.** OpenStreetMap places through a server-side Overpass proxy: free drinking water, shops selling water or ORS, and shaded or AC places, with walking times and a "10-minute break" pick. The location stays on the phone.
- **AI chat assistant.** Workers ask in their own words, in English or Hindi. A Strands agent on Bedrock answers by calling HeatShift's own tools (`get_plan`, `get_trip`, `find_places`), so it never invents a temperature. Emergency words skip the AI and go straight to 108/112.
- **First-visit setup.** Job, city, language and optional work hours are saved on the phone, and danger hours inside the worker's shift are pointed out. There are no accounts and no database.
- **Two cities, Delhi and Ahmedabad.** Ahmedabad had India's first heat action plan. It was added with one JSON entry and no code changes.
- **The data source, last-updated time, Open-Meteo attribution and a "prototype, not medical advice" note**, always visible.

Because it is October, the app can **replay real 2024 Delhi heatwave days** from the Open-Meteo archive:
- 18 June 2024, feels like 47°C
- 29 May 2024, dry 46°C

### How the numbers are made

1. Hourly temperature and humidity come from Open-Meteo: the forecast API, or the archive for replay.
2. The heat index uses the NWS Rothfusz equation with its humidity adjustments.
3. Levels use the NWS Heat Index Chart bands, converted to °C and stored per city in `cities.json`, so cities can set local thresholds.
4. **The IMD floor:** air at 45°C or above is at least Danger, and 47°C or above is Extreme. Without this, dry Delhi heat (46°C at 10% humidity gives a heat index of only about 43°C) would be under-rated.
5. Each worker profile maps the level to rest, water and avoid-hours. Heavy work gets more rest, and vendors get "shade" instead of "stop".

## Where AWS fits

HeatShift covers both of the event's AWS paths: **Build It** (Strands Agents, an AWS open-source tool) and **Ship It** (deployed on AWS: Elastic Beanstalk on EC2, with S3 and Bedrock). The demo video shows the running Beanstalk environment, the live URL and the server logs of Bedrock calls.

- **AWS Elastic Beanstalk** hosts the Flask app: Python 3.12 on Amazon Linux 2023, single instance, in ap-southeast-2. I deploy from the CLI with a small PowerShell script that zips the app, uploads it to S3, creates a version, updates the environment, waits for Ready and checks `/health`.
- **Strands Agents with tool use** powers the chat assistant. The agent's tools are HeatShift's own deterministic functions (plan, trip, places). Bedrock decides which tool to call, and the answer can only contain numbers the tools returned.
- **Strands Agents**, AWS's open-source agent SDK, also runs the advice agent. Its system prompt only allows the numbers HeatShift computed: no invented temperatures, no lists, plain words, Hindi in Devanagari.
- **Amazon Bedrock** (Amazon Nova Lite, in-Region in Sydney) writes the message through the Converse API. Model and region are environment variables.
- **IAM instance role:** the server calls Bedrock with its role, so there are no keys anywhere.

The AI is never in the critical path. Bedrock calls have an 8-second limit, a one-minute cooldown after a failure, and output checks (length, and Devanagari script for Hindi). Any failure returns template text in the same language.

## Challenges

- **Dry heat breaks the heat index.** Delhi's worst pre-monsoon days are hot and very dry, and the heat index can read below the air temperature. Adding IMD's heat wave rules as a floor fixed that.
- **Bedrock on a brand-new AWS account.** Cross-Region inference profiles were blocked while the account was being verified, and Anthropic models need a use-case form. I used an in-Region model (Nova Lite in Sydney) and made the model a config value, so switching later needs no code change.
- **No access keys.** The account uses `aws login` console credentials. The Beanstalk console kept failing with "security token invalid", so I moved deploys to the CLI.
- **Making it usable outside the team.** That meant big tap targets, a light high-contrast theme for sunlight, Hindi throughout, colour always paired with a text label, and read-aloud.

## Impact and what's next

HeatShift turns a warning into a plan for the day, specific to the job. What's next:

1. **More cities, each with its own thresholds.** Adding a city is one JSON entry.
2. **SMS / WhatsApp / IVR delivery** of the morning plan, for workers without smartphones or data.
3. **An employer and contractor view**, so a site supervisor sees the same stop window as the worker.
4. **Calibrating the profiles with worker unions and public-health researchers**, and adding a direct-sun correction.
5. **Water-point and shade maps**, linking to the WIEGO finding on drinking water.

## AI tools used

- **Claude Code**, used inside the **Antigravity** IDE: planning, code, tests and documentation. I reviewed and tested everything it produced.
- **Amazon Bedrock (Amazon Nova Lite) through Strands Agents**: generates the advice message inside the app.
