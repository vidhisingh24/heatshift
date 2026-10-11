# HeatShift: submission writeup

The video shows: the README with the architecture, the live app on CloudFront, and the AWS console with Elastic Beanstalk, CloudFront and Bedrock.

**Track:** Heat and Water · **Live:** https://d2rsnmdxkrj7b8.cloudfront.net · **Video:** https://youtu.be/TatXWYDK8GY · **Repo:** https://github.com/vidhisingh24/heatshift

## The problem

India's heat action plans warn about temperature but rarely tell outdoor workers what to do hour by hour. A Centre for Policy Research review of 37 plans found only 10 set local thresholds and only 2 assessed who is vulnerable (Pillai & Dalal, 2023). In a WIEGO survey of around 500 Delhi street vendors in 2025, 89% had no free, clean drinking water at work ([Question of Cities](https://questionofcities.org/mapping-heat-stress-shows-delhi-street-vendors-precarity/)).

## What HeatShift does

A mobile web app in English and Hindi for street vendors, delivery riders and construction workers. There are no accounts. It asks four questions once (language, job, working hours, location), then opens on today's forecast.

- **Home:** one line ("Avoid 12:00–16:00. Best: 05:00–08:00"), a 24-hour colour bar, rest and water rules, and danger hours inside your shift.
- **Safe trip:** "I must go out at 2 PM" gives the risk, a job-specific checklist (NCDC and NDMA guidance), a cooler time, and 108/112.
- **Nearby:** drinking water, ORS shops and shade from OpenStreetMap, with walking times.
- **Ask:** questions in Hindi, Hinglish or English, answered only from HeatShift's own data.
- **Day plan:** shift blocks, chart, read-aloud, WhatsApp share and a printable poster.

The level comes from the NWS heat index (Open-Meteo hourly temperature and humidity), with IMD heatwave floors on top (air ≥ 45°C is Danger, ≥ 47°C is Extreme), so dry heat isn't under-rated.

## Where AWS fits

Both paths are covered: **Build It** and **Ship It**.

- **CloudFront:** the HTTPS link. Phones only share location over HTTPS. Caching is off and POST is forwarded.
- **Elastic Beanstalk:** the Flask app on EC2 in Sydney, deployed by a CLI script that goes through S3.
- **Strands Agents with Amazon Bedrock (Nova Lite):** writes the daily advice and powers the chat. The chat agent's tools are HeatShift's own functions (plan, trip, places), so it can't invent temperatures.
- **IAM role:** lets the server call Bedrock with no keys in the code.

If Bedrock fails, the app returns fixed text in the same language.

## Challenges

- Dry heat can read lower than the air temperature; the IMD floor fixes this.
- Cross-Region Bedrock was blocked on a new account, so I used an in-Region model.
- Location needs HTTPS, so CloudFront was added.
- Workers type Hindi in English letters, so the chat detects Hinglish.

## What's next

Thresholds set with city health departments, SMS or WhatsApp alerts, an employer view, and more cities (each city is one JSON entry).

## AI tools used

Claude Code in the Antigravity IDE (planning, code, tests, docs; all reviewed and tested by me). Amazon Bedrock Nova Lite via Strands Agents inside the app.
