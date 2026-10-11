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
| 0:20–0:35 | **AWS console**, Sydney region visible: Elastic Beanstalk → `heatshift-env`, **Health: Ok**, Python 3.12. Click the environment URL. | "It's live on AWS Elastic Beanstalk in Sydney." |
| 0:35–0:55 | **Phone view** (DevTools device toolbar; clear site data first so setup appears). The **setup screen**: tap हिंदी then back to English, tap **Delivery rider**, set work hours 09–18, then **Show my plan**. | "First visit: pick your job, city and language. It's saved on the phone, with no account." |
| 0:55–1:20 | The plan: the **rule line** "Avoid 12:00–16:00. Best: …", the **shift warning**, the **24-hour bar**, the big **47°C** and "Why Danger?". Scroll through **Your shift plan**. | "A replay of a real 2024 Delhi heatwave day. It feels like 47. Avoid 12 to 4, and here are the danger hours inside *my* shift." |
| 1:20–1:45 | **I can't avoid this time:** 14:00 for 2 hours, then **Check my trip**. Show Danger, the **safer time**, the checklist, and the red **108 / 112** box. | "But a rider often can't skip the 2 PM order. So: the risk for that trip, the nearest cooler time, a checklist for riders, and when to stop and call 108." |
| 1:45–2:05 | **Find water / shade near me**. Show the 10-minute break picks, the map and the list with walking minutes. | "Where to drink water, buy ORS or sit in shade, from OpenStreetMap, with walking times. The location never leaves the phone except for this lookup." |
| 2:05–2:35 | **Chat**: tap the chip **"I must go at 2 PM"**. The answer appears with **AI (Amazon Bedrock)**. Then type in Hindi **"मुझे पानी कहाँ मिलेगा?"** and show real place names in Hindi. | "And they can just ask, in Hindi or English. A Strands agent on Amazon Bedrock calls our own plan, trip and places tools, so it never invents a temperature. If Bedrock fails, the checklist answers instead." |
| 2:35–2:48 | Tap **हिंदी** for the full Hindi page; tap **सुनें** (Listen) for 2 s. Scroll to the footer credits and the disclaimer. | "Everything works in Hindi, and it can read the plan aloud. It's a prototype, not medical advice." |
| 2:48–2:55 | **Text card:** "HeatShift · github.com/vidhisingh24/heatshift". | "HeatShift: from a heat warning to a plan for the day." |

## If something goes wrong while recording
- **Console Logs won't download:** show the live API instead. Open `<live URL>/api/plan?city=delhi&role=rider&lang=hi&date=2024-06-18` in a browser tab and point at `"message_source": "bedrock:amazon.nova-lite-v1:0"`, which proves the message came from Bedrock on the live server.
- **Bedrock fails:** the app shows "Standard advice text". Say "the AI writer is unavailable, so the template takes over". That demonstrates the fallback.
- **Over 3:00:** cut the setup step (0:35–0:55) first, then the Listen step.
- **To show setup again:** DevTools → Application → Local storage → delete `heatshift.profile`, or use the **Change** link in the header.
