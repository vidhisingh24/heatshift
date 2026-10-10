# HeatShift: 3-minute demo script

**Before recording:**
- Run `aws login`.
- Open the AWS console in **Asia Pacific (Sydney)**, on Elastic Beanstalk → `heatshift-env`.
- In a second browser window, open the live URL with DevTools → device toolbar set to a phone, around 390px wide.
- Open the app once, so the Bedrock message is cached and loads instantly.
- No news photos; use text-only cards.

**Recording:** OBS or the Windows Snipping Tool recorder, 1080p. Record the console and the app as separate takes and join them.

| Time | Screen | Voiceover |
|---|---|---|
| 0:00–0:20 | Text card: **"Heatwave alert: 44°C." Now what?** Below it: "37 heat action plans reviewed, only 10 with local thresholds (CPR, 2023)" and "89% of surveyed Delhi street vendors lack free clean water (WIEGO)". | "India's heat plans warn about temperature. They don't tell a delivery rider whether to take the 1 PM order, or a construction worker how long to rest." |
| 0:20–0:40 | AWS console: Elastic Beanstalk, region **Sydney** visible top right, `heatshift-env` with **Health: Ok**, platform Python 3.12. Click the environment URL. | "HeatShift is live on AWS Elastic Beanstalk. This is the running environment, and here's the URL." |
| 0:40–1:25 | Phone view of the app. Pick **Delivery rider** and **Heatwave replay: 18 Jun 2024**. Point at the **Danger** band, the coloured strip, "No deliveries 12:00–16:00", rest 20 min, water every 20 min. Scroll the hour-by-hour list. | "It's October, so I'm replaying a real Delhi heatwave day. 44 degrees, but with humidity it feels like 47. For a rider: no deliveries from 12 to 4, rest 20 minutes each hot hour, water every 20 minutes, and the best hours to work." |
| 1:25–1:50 | Tap **Construction worker**: rest goes to 30 min, water to 15. Tap **Street vendor**: "Stay in shade" instead of stop. | "Same weather, different job, different plan. Heavy work gets more rest; a vendor who can't leave the stall gets shade advice." |
| 1:50–2:15 | Tap **हिंदी**. The whole page switches. Tap **सुनें** (Listen) and let it read 3–4 seconds. | "One tap for Hindi, and a Listen button for workers who'd rather hear it than read it." |
| 2:15–2:35 | Point at the line under the advice: "Written by Amazon Bedrock (Amazon Nova Lite) using Strands Agents". Then open `/api/plan?role=rider&lang=hi&date=2024-06-18` in a tab and point at `message_source`. | "The advice is written by a Strands agent on Amazon Bedrock, using only the numbers we computed. If Bedrock is slow or down, template text in the same language takes over, so the app never breaks." |
| 2:35–2:50 | Change the day to **29 May 2024 (dry, 46°C)**. Show Danger even though feels-like is lower than air. Scroll to the legend note and the footer: data source, updated time, "Weather data by Open-Meteo.com (CC BY 4.0)", disclaimer. | "In dry heat the heat index can read low, so we add IMD's heat wave rule: 45 degrees air is at least Danger. Data source and update time are always on screen." |
| 2:50–3:00 | Text card: repo URL, "Next: more cities with local thresholds, SMS and WhatsApp, employer view". | "HeatShift: from a heat warning to a plan for the day." |

**Fallback if Bedrock fails while recording:** keep going. The app shows "Standard advice text". Say "the AI writer is unavailable right now, so the template takes over", which demonstrates the fallback.
