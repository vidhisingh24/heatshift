# Turning a heat forecast into a work schedule for India's outdoor workers

*AWS Builder Center draft · Vidhi Singh*

## 1. A rider's afternoon at 44°C

A delivery rider in Delhi opens a weather app and sees "44°C, heatwave alert". The app stops there. It doesn't say whether to take the 1 PM order, how long to rest, or how often to drink water. HeatShift tries to answer exactly those questions.

## 2. The gap

- CPR's review of 37 Indian heat action plans found that few use locally defined thresholds or assess who is vulnerable. *(cite and verify)*
- WIEGO found that most surveyed Delhi street vendors had no free drinking water at work. *(cite and verify)*

Warnings exist. What workers don't have is a plan for each hour.

## 3. The heat math, and why dry heat needs a floor

- NWS heat index (Rothfusz regression) plus its humidity adjustments, in about 20 lines of Python.
- The surprise: 46°C at 10% humidity gives a heat index of only about 43°C, so the heat index alone would under-warn.
- The fix: IMD heat wave rules as a floor. 45°C air is at least Danger, and 47°C is Extreme.
- Thresholds live per city in JSON, which is the "local thresholds" point from CPR.

## 4. Strands Agents + Amazon Bedrock, with a fallback

Show `advice.py`:
- `BedrockModel(model_id=..., region_name=..., streaming=False)` plus a botocore timeout.
- A fresh `Agent` for each request (no shared history), `callback_handler=None`.
- A system prompt that only allows the computed numbers.
- Output checks, including Devanagari for Hindi.
- Any failure returns template text. "The AI is never in the critical path."

## 5. Deploying Flask to Elastic Beanstalk from Windows, without access keys

- `aws login` on a new-builder account: no IAM access keys; console credentials last about 12 hours.
- The ZIP must have its files at the root. `tar -a -c -f app.zip ...` on Windows writes `/` paths, which Beanstalk accepts.
- `.gitattributes` with `eol=lf`, so the `Procfile` doesn't break gunicorn on Linux.
- `deploy.ps1`:
  1. `aws s3 cp`
  2. `create-application-version`
  3. `update-environment`
  4. Poll `describe-environments`
  5. Check `/health`
- The instance role (`AWSElasticBeanstalkWebTier` and `AmazonBedrockFullAccess`) means no secrets in the app.

## 6. Finding a usable Bedrock model in Sydney

- `aws bedrock list-inference-profiles` shows `au.` / `apac.` / `global.` IDs. Those were blocked while the account was being verified.
- `aws bedrock list-foundation-models --by-inference-type ON_DEMAND` shows in-Region models. Amazon Nova Lite worked straight away.
- Anthropic models need a one-time use-case form.
- Lesson: put the model ID in an environment variable from day one.

## 7. What's next

More cities, SMS/WhatsApp delivery, an employer view, and calibration with worker groups.

Links: repo, live app, demo video.
