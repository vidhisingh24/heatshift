# HeatShift: submission writeup

The video shows: the README with the architecture, the live app on CloudFront, and the AWS console with Elastic Beanstalk, CloudFront and Bedrock.

**Track:** Heat and Water · **Live:** https://d2rsnmdxkrj7b8.cloudfront.net · **Video:** https://youtu.be/TatXWYDK8GY · **Repo:** https://github.com/vidhisingh24/heatshift

## The problem

India's heat action plans warn about temperature, but they rarely tell an outdoor worker what to do hour by hour. A Centre for Policy Research review of 37 plans found only 10 set locally defined thresholds, and only 2 assessed who is vulnerable (Pillai & Dalal, 2023). Street vendors, delivery riders and construction workers can't stay indoors. In a WIEGO survey of around 500 Delhi street vendors in 2025, 89% had no free, clean drinking water at work ([Question of Cities](https://questionofcities.org/mapping-heat-stress-shows-delhi-street-vendors-precarity/)).

## What HeatShift does

A mobile-first web app in English and Hindi. There are no accounts. On the first visit it asks four questions: language, job, working hours and location. After that it opens straight on today's forecast.

- **Home:** one line, such as "Avoid 12:00–16:00. Best: 05:00–08:00, 19:00–22:00", plus a 24-hour colour bar, the rest and water rule, and a warning for danger hours inside the worker's own shift.
- **Safe trip:** "I have to go out at 2 PM for 2 hours" gives the risk, a checklist for that job (based on NCDC and NDMA guidance), the nearest cooler time, and a red box with 108/112.
- **Nearby:** free drinking water, shops selling water or ORS, and shaded or AC places from OpenStreetMap, with walking time and a "10-minute break" pick. The location stays on the phone.
- **Ask:** questions in plain Hindi, Hinglish or English. The AI answers only from HeatShift's own data, and emergency words go straight to 108/112.
- **Day plan:** shift blocks, an hourly chart, read-aloud, WhatsApp share and a printable poster for a site or stall.

**How the level is set.** The NWS heat index comes from hourly temperature and humidity (Open-Meteo), mapped to four levels. IMD heatwave rules are added on top: air ≥ 45°C is at least Danger and ≥ 47°C is Extreme, so dry heat isn't under-rated. The thresholds are stored per city.

## Where AWS fits

HeatShift covers both paths: **Build It** and **Ship It**.

- **Amazon CloudFront:** the public HTTPS link. Phones only share location over HTTPS. Caching is off and POST is forwarded for chat.
- **AWS Elastic Beanstalk:** runs the Flask app (Python 3.12, Amazon Linux 2023, EC2 t3.small, Sydney). It is deployed from the CLI with a script that uploads to S3, updates the environment and checks `/health`.
- **Strands Agents with Amazon Bedrock (Nova Lite, in-Region):** two agents. One writes the daily advice. The other is the chat assistant, whose tools are HeatShift's own functions (`get_plan`, `get_trip`, `find_places`), so it can't invent a temperature or a place.
- **IAM instance role:** lets the server call Bedrock with no keys in the code.

The AI is never in the critical path. Timeouts, output checks and a rate limit apply, and any failure returns deterministic text in the same language.

## Challenges

- Dry Delhi heat can make the heat index read lower than the air temperature; the IMD floor fixed that.
- On a new AWS account, cross-Region Bedrock profiles were blocked at first, so I used an in-Region model and made the model a setting.
- Location needs HTTPS, so CloudFront was added in front of Beanstalk.
- Workers write Hindi in English letters, so the chat detects Hinglish and answers in Hindi.

## What's next

Local thresholds set with city health departments, SMS or WhatsApp morning alerts for workers without smartphones, an employer view, and more cities. A city is one JSON entry.

## AI tools used

Claude Code in the Antigravity IDE, for planning, code, tests and docs, all reviewed and tested by me. Amazon Bedrock (Nova Lite) via Strands Agents inside the app.
