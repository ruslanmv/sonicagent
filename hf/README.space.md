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

SonicAgent is a self-hosted speech service for English and Italian. This Space runs the same FastAPI application used on a local PC. It transcribes microphone audio with multilingual Whisper (`faster-whisper` / CTranslate2, CPU INT8 by default). Optional Piper speech synthesis is off unless voice files and `SONIC_TTS_ENABLED` are configured.

The Space is a remote processor. Audio sent here leaves the headset or browser. It is not on-device and it is not an offline Quest mode.

## API

Authenticated routes:

- `GET /v1/audio/capabilities`
- `POST /v1/audio/transcriptions`
- `POST /v1/audio/speech` (only when Piper is actually installed and enabled)

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
