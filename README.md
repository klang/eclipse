# Eclipse Commentator SPA

A standalone, offline-capable single-page application that provides real-time play-by-play audio commentary during the **total solar eclipse of 12 August 2026**, observed from **Antoñán del Valle, León, Spain** (42.5°N, 5.9°W).

The app works like a sports commentator: it automatically announces each phase of the eclipse at the precise moment it occurs, with bilingual audio narration in English and Spanish.

## Eclipse Data

| | UTC | CEST (local) |
|---|---|---|
| **C1** — First contact | 17:32:40 | 19:32:40 |
| **C2** — Second contact (totality begins) | 18:28:32 | 20:28:32 |
| **Maximum eclipse** | 18:29:18 | 20:29:18 |
| **C3** — Third contact (totality ends) | 18:30:04 | 20:30:04 |
| **C4** — Fourth contact | 19:22:12 | 21:22:12 |

- **Totality duration**: 92 seconds (1 min 32 sec)
- **Magnitude**: 1.010
- **Sun altitude at maximum**: ~21°

Contact times computed from NASA Besselian elements for the specific observation coordinates.

Main reference: [timeanddate.com eclipse page for Antoñán del Valle](https://www.timeanddate.com/eclipse/in/@3129949?iso=20260812)

## Features

- **36 timestamped events** covering: pre-eclipse warmup (30 min before C1), partial ingress phases, totality approach, second contact / diamond ring / chromosphere / corona / Baily's beads / maximum / third contact, partial egress, sunset, and fourth contact
- **68 audio clips** (34 English + 34 Spanish) embedded as base64, generated with Microsoft Edge TTS — no network requests at runtime
- **Bilingual toggle** — switch between English and Spanish commentary at any time
- **SVG eclipse animation** — sun disc with gradient, moon transit across the sun, corona glow during totality, chromosphere ring at C2/C3
- **Real-time clock** (CEST) with countdown to the next event
- **Safety banners** — red "GLASSES REQUIRED" during partial phases, green "GLASSES OFF — TOTALITY" during totality
- **Scrollable event timeline** with played / active / upcoming visual states
- **Sun position display** — altitude, azimuth, and compass direction
- **Audio controls** — mute, volume slider, auto-play mode
- **Debug mode** — gear icon reveals time-jump buttons (C1, C2, max, C3, C4) and a speed slider (1x–300x) for pre-event walkthrough
- **Fully offline** — everything is in one HTML file, no external requests
- **Mobile-optimized** — 600px max-width, touch-friendly controls, PWA meta tags

## Usage

### Open locally

Open `eclipse.html` in any modern browser. That's it. No server, no build step, no dependencies.

On a phone, you can:
1. Transfer the file directly and open it in the browser
2. Deploy to AWS (see below) and load the URL — the page works offline once loaded

### Language

Tap the **EN / ES** toggle to switch commentary language. Both audio and text update immediately.

### Debug mode

Tap the gear icon (⚙) in the header to reveal debug controls:
- **Time jump buttons** — jump to 1 minute before C1, C2, maximum, C3, or C4
- **Speed slider** — accelerate time from 1x to 300x to walk through the entire eclipse in minutes
- **Reset** — return to real-time clock

This is useful for testing the app before eclipse day.

## AWS Deployment

The app is designed to be served from S3 behind CloudFront, so you can load it on your phone via HTTPS and then use it offline.

### Prerequisites

- AWS CLI installed and configured
- SSO login completed: `aws sso login --profile sandbox`
- Sufficient IAM permissions for CloudFormation, S3, CloudFront, IAM, ACM, Route 53

### Deploy without custom domain

```bash
./deploy.sh
```

Defaults: stack name `eclipse`, region `eu-west-1`, profile `sandbox`.

### Deploy with custom domain

```bash
DOMAIN_NAME=eclipse.eclipse.lang.dk ./deploy.sh
```

The deploy script will:
1. Validate the CloudFormation template
2. Deploy/update the stack (S3 bucket, CloudFront distribution, and optionally ACM certificate + Route 53 records)
3. Upload `eclipse.html` as both `index.html` and `eclipse.html` to S3
4. Invalidate the CloudFront cache

First deployment takes 5–10 minutes (longer with a custom domain due to certificate provisioning).

### Update just the SPA (no infrastructure changes)

```bash
BUCKET=<bucket-name> CF_DIST=<distribution-id>

aws s3 cp eclipse.html "s3://${BUCKET}/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache" --profile sandbox

aws s3 cp eclipse.html "s3://${BUCKET}/eclipse.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache" --profile sandbox

aws cloudfront create-invalidation \
  --distribution-id "${CF_DIST}" --paths "/*" --profile sandbox
```

### Custom parameters

```bash
./deploy.sh <stack-name> <region> <profile>
```

For example: `./deploy.sh eclipse eu-west-1 production`

## Audio Regeneration

The audio clips are already embedded in `eclipse.html`. To regenerate them (e.g., after editing commentary text):

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install edge-tts
```

### Generate and inject

```bash
python3 generate-audio.py    # creates audio/{en,es}/*.mp3 and audio-clips.js
python3 inject-audio.py      # replaces AUDIO_CLIPS in eclipse.html (backs up to .bak)
```

### Voices

- English: `en-US-GuyNeural` (Microsoft Edge TTS)
- Spanish: `es-ES-AlvaroNeural` (Microsoft Edge TTS)

### Optional: ElevenLabs upgrade

For higher-quality dramatic narration on ~15 key moments (totality, diamond ring, etc.):

```bash
pip install elevenlabs
ELEVENLABS_API_KEY=your_key python3 generate-audio-elevenlabs.py
python3 inject-audio.py
```

Requires an ElevenLabs account (free tier provides ~10,000 characters/month).

## Project Structure

```
timeanddate/
  eclipse.html                  — the SPA (~5.9 MB with embedded audio)
  eclipse.html.bak              — pre-injection backup
  template.yaml                 — CloudFormation template (S3 + CloudFront + ACM + Route 53)
  deploy.sh                     — AWS deployment script
  generate-audio.py             — edge-tts audio generation (36 events x 2 languages)
  generate-audio-elevenlabs.py  — ElevenLabs upgrade for dramatic moments
  inject-audio.py               — embeds audio-clips.js into eclipse.html
  audio-clips.js                — generated base64 audio data (intermediate file)
  audio/
    en/                         — 34 English MP3 clips
    es/                         — 34 Spanish MP3 clips
  .venv/                        — Python virtual environment
  inspiration/                  — original CloudFormation template and deploy script (reference)
```

## How It Works

The SPA runs entirely client-side. On load, it initializes the `EclipseApp` class which:

1. Starts a real-time clock synced to CEST (UTC+2)
2. Loads the 36-event timeline with pre-computed UTC timestamps
3. Checks the current time against the event schedule every 100ms
4. When an event's timestamp is reached, it highlights the event in the timeline, displays the commentary text, and plays the corresponding audio clip
5. Updates the SVG animation to show the moon's position relative to the sun
6. Shows/hides safety banners based on the current eclipse phase

All astronomical calculations (contact times, sun position, moon position) are hard-coded for the specific location and date, computed from NASA Besselian elements. No runtime geolocation or API calls are needed.
