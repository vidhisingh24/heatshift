# Submission checklist (from wemakedevs.org/aws/env and /aws/rules)

A submission is three things: **a public repo**, **a YouTube demo under 3 minutes**, and **a short writeup**. Deadlines are strict; the form closes at the deadline.

## Must-haves
- [x] Public repo: https://github.com/vidhisingh24/heatshift (history dated 10–11 Oct 2026, within the event)
- [x] Uses AWS: Strands Agents (Build It) + Elastic Beanstalk / EC2 / S3 / Bedrock (Ship It)
- [x] AI coding tools listed in the writeup (Claude Code, Antigravity)
- [x] Third-party code and data credited with licenses (README → Third-party credits)
- [ ] **AWS Builder Center profile with university enrollment verified**
- [ ] **Demo video** recorded from `docs/demo-script.md`:
  - [ ] **under 3:00**
  - [ ] shows the AWS console (Beanstalk Health Ok, the URL, logs)
  - [ ] uploaded to **YouTube** as Public or Unlisted
  - [ ] **opened in an incognito / signed-out browser** to check the link works
- [ ] **Writeup** pasted from `docs/writeup.md`, with the video link added
- [ ] **Two facts verified, then the "verify" markers removed** from README.md, docs/writeup.md and docs/blog.md:
  - [ ] CPR (2023): "only 2 of 37 plans assessed vulnerability"
  - [ ] WIEGO: exact title and sample size (519?)
- [ ] Track selected: **Heat and Water**
- [ ] Submitted before the deadline on the event page

## Optional: Top 5 blogs prize (AirPods)
- [ ] Publish `docs/blog.md` on **AWS Builder Center**. Upload `docs/screenshots/*.png` as images and add the YouTube link.
- [ ] Put the blog link in the submission form.

## Before recording
- [ ] Open the live URL once on each screen so Bedrock messages are cached
- [ ] `aws login` and the console open in Sydney

## After judging
- [ ] `aws elasticbeanstalk terminate-environment --region ap-southeast-2 --environment-name heatshift-env` (stops credit usage of about $0.80/day)
