---
title: SonicAgent
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: gpl-3.0
---

# SonicAgent

SonicAgent is a self-hosted speech service. This Space runs the same FastAPI application used on a local PC. It transcribes microphone audio with multilingual Whisper (`faster-whisper` / CTranslate2, CPU INT8) in English, Spanish, French, German, Italian, and Portuguese. It speaks with the Piper voices in `ruslanmv/hp-piper-voices`. Where a female speaker exists, Companion is warmer and slower and Secretary is clearer and a little faster. Every other speaker stays under its own language and keeps its published gender, including the male Portuguese voices. Selecting Italiano lists Italian voices only.

The Space is a remote processor. Audio sent here leaves the headset or browser. It is not on-device and it is not an offline Quest mode.

## Voice Studio

Open the **App** tab to use the responsive SonicAgent Voice Studio at `/`.
Record your microphone or upload audio, transcribe with Whisper, and try
Piper TTS when a voice is installed. The UI also displays live model
readiness. The previous JSON root response is at `/api-info`; the full
OpenAPI documentation remains at `/docs`.

**Private by default:** The production API uses a bearer service token.
The browser interface keeps a manually entered token in tab memory only,
but owners should not enter a shared production secret on public machines.

**Optional public visitors:** Set `SONIC_PUBLIC_DEMO_ENABLED=true` in the
Space Variables to enable a bounded anonymous speech-to-text demo.
`SONIC_PUBLIC_DEMO_TTS_ENABLED=true` separately enables voice synthesis
when Piper is ready. Public demo traffic consumes your CPU capacity and
may incur hosting costs. See `hf/README.md` in the GitHub repository
for rate limits and security constraints.

## API

Authenticated routes:

- `GET /v1/audio/capabilities`
- `POST /v1/audio/transcriptions`
- `POST /v1/audio/speech` returns a WAV file for Lessac (English) and Paola (Italian)

Public process checks:

- `GET /health/live` — process is up. This does not mean the model is loaded.
- `GET /health/ready` — `ready: true` only after Whisper is loaded.

Send `Authorization: Bearer <SONIC_API_KEY>`. Put that value in a private Space secret named `SONIC_API_KEY`. Do not put it in this README or in the image.

OllaBridge Cloud should call this Space server-side. The 3D Avatar browser must not receive the SonicAgent credential.

## Models and limits

The image is built around multilingual `whisper-tiny` so Italian is supported. English-only checkpoints such as `tiny.en` are rejected. The default recording limit is 15 seconds and 2 MiB. Audio and transcripts are not stored.

CPU Basic Spaces can sleep, cold-start, and run out of memory. A sleeping Space should be reported as warming or unavailable. This deployment does not promise always-on or unlimited free inference.

## Privacy

Do not enable `SONIC_STORE_AUDIO` or `SONIC_LOG_TRANSCRIPT_CONTENT` on a shared Space. Logs record request ids, durations, and error codes only.
