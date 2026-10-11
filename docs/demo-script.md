# HeatShift: demo video script (target 2:45, hard limit under 3:00)

## Official video rules
- Upload to **YouTube**, set to **Public or Unlisted**.
- It must **run under three minutes**. Aim for 2:45 to leave a margin.
- **Open the link in a signed-out / incognito browser** before submitting.
- AWS must be **shown running** in the video. Naming it is not enough.

## Before recording
1. Run `aws login`. Open the AWS console in **Asia Pacific (Sydney)** → Elastic Beanstalk → `heatshift-env`.
2. In another window, open the live URL in Chrome or Edge → DevTools → device toolbar → a phone of about 390px. Zoom the page to 125% so text is readable on YouTube.
3. **Warm the cache:** click through rider, construction and vendor in EN and HI on both replay days once, so every screen loads instantly.
4. Fetch the logs once in the console (Logs → Request logs → **Last 100 lines**), so the download is ready.
5. Use text-only title cards; no news photos. Record at 1080p with OBS or the Windows Snipping Tool recorder. Record each segment as a separate take and join them.

## Script (follows the judging order: idea and impact → AWS → design → works)

| Time | Screen | Voiceover |
|---|---|---|
| 0:00–0:20 | **Text card:** "Heatwave alert: 44°C." *Now what?* Below: "37 heat action plans reviewed, only 10 with local thresholds (CPR, 2023)" and "89% of surveyed Delhi street vendors lack free clean water (WIEGO)". | "India's heat plans warn about temperature. They don't tell a delivery rider whether to take the 1 PM order, or a construction worker how long to rest. HeatShift turns the forecast into a plan for their day." |
| 0:20–0:40 | **AWS console**, Sydney region visible: Elastic Beanstalk → `heatshift-env`, **Health: Ok**, Python 3.12, running version. Click the environment URL. | "It's live on AWS Elastic Beanstalk in Sydney. This is the running environment. I'll open its URL." |
| 0:40–1:20 | **Desktop view** (it looks best at full width). Delivery rider, Delhi, heatwave replay 18 Jun 2024. Point at **Danger** and the big **47°C**, then the three numbers: no deliveries 12:00–16:00, rest 20 min, water every 20 min. Scroll to **Your shift plan** (the blocks), then hover the **chart** at 14:00 to show the tooltip. | "It's October, so I replay a real 2024 Delhi heatwave day. Air 44, but with humidity it feels like 47. For a rider the day becomes a shift plan: work with breaks in the morning, stop from 12 to 4, and back to work in the evening. Hover any hour for the details." |
| 1:20–1:40 | Tap **Construction worker** (rest 30 min, water 15). Tap **Street vendor** ("Shade or cover stall"). | "Same weather, different job. Heavy work gets more rest. A vendor who can't leave the stall is told to move into shade." |
| 1:40–2:05 | Switch to the **phone view** (DevTools device toolbar). Tap **हिंदी**. Tap **सुनें** (Listen) for 3 seconds. Point at **WhatsApp पर भेजें** and **प्रिंट या PDF**. | "On a phone, in Hindi, in one tap. Listen reads it aloud. Share sends it to a WhatsApp group, and Print makes a notice a contractor can pin up at the site." |
| 2:05–2:25 | Point at the line under the advice: "Written by Amazon Bedrock (Amazon Nova Lite) using Strands Agents". Switch to the console: **Logs → Last 100 lines**, find `message_source=bedrock:amazon.nova-lite-v1:0` in `web.stdout.log`. | "The advice is written by a Strands agent on Amazon Bedrock, using only the numbers we computed. Here it is in the server logs. If Bedrock fails, template text in the same language takes over." |
| 2:25–2:40 | Back to the app: switch the city to **Ahmedabad** (replay 27 May 2024). Scroll to the footer: data source, updated time, "Weather data by Open-Meteo.com (CC BY 4.0)", disclaimer. | "Adding a city is one JSON entry: here's Ahmedabad. Data source and update time are always on screen, and it says plainly it's a prototype, not medical advice." |
| 2:40–2:48 | **Text card:** "HeatShift · github.com/vidhisingh24/heatshift" and "Next: local thresholds per city · SMS/WhatsApp alerts · employer view". | "HeatShift: from a heat warning to a plan for the day." |

## If something goes wrong while recording
- **Console Logs won't download:** show the live API instead. Open `<live URL>/api/plan?city=delhi&role=rider&lang=hi&date=2024-06-18` in a browser tab and point at `"message_source": "bedrock:amazon.nova-lite-v1:0"`, which proves the message came from Bedrock on the live server.
- **Bedrock fails:** the app shows "Standard advice text". Say "the AI writer is unavailable, so the template takes over". That demonstrates the fallback.
- **Over 3:00:** cut the hour-list scroll (0:40–1:20) and the Ahmedabad step first.
