# REST API

The REST API is the normal HTTP interface. It is used for health checks, session
creation, model/voice information, and metrics.

## Useful local endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health/live` | Confirms the process is alive. |
| `GET /health/ready` | Reports whether required runtime pieces are ready. |
| `POST /v1/sessions` | Creates a voice session and returns WebSocket details. |
| `GET /v1/voices` | Lists every Piper voice in the registry, with role, gender, quality, and whether that file is installed on this machine. |
| `GET /v1/models/stt` | Lists known speech-to-text models. |
| `GET /metrics` | Prometheus-style metrics. |
| `GET /v1/audio/capabilities` | Bearer token. Reports STT and TTS readiness. |
| `POST /v1/audio/transcriptions` | Bearer token. Multipart audio in, JSON transcript out. |
| `POST /v1/audio/speech` | Bearer token. Optional Piper WAV. Returns 503 when TTS is not installed. |

## Session creation in plain language

Before the browser can stream microphone audio, it asks the backend to create a
session. The backend returns a session ID, a resume token, and the WebSocket URL.

## Current status

`/v1/sessions` is still a development session scaffold. Do not treat its token as a speech credential.

`/v1/audio/transcriptions` requires `SONIC_API_KEY`. `/health/live` can return 200 while `/health/ready` is false. Field details, error codes, and the local and Space deploy steps are in `hf/README.md` and [Speech recognition](../speech-recognition.md).
