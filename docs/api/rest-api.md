# REST API

The REST API is the normal HTTP interface. It is used for health checks, session
creation, model/voice information, and metrics.

## Useful local endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health/live` | Confirms the process is alive. |
| `GET /health/ready` | Reports whether required runtime pieces are ready. |
| `POST /v1/sessions` | Creates a voice session and returns WebSocket details. |
| `GET /v1/voices` | Lists known voices. |
| `GET /v1/models/stt` | Lists known speech-to-text models. |
| `GET /metrics` | Prometheus-style metrics. |
| `GET /v1/audio/capabilities` | Bearer token. Reports STT, TTS, the full-turn socket, and the speech-only stream. |
| `POST /v1/audio/transcriptions` | Bearer token. Multipart audio in, JSON transcript out. |
| `POST /v1/audio/speech` | Bearer token. Optional Piper WAV. Returns 503 when TTS is not installed. |
| `POST /v1/audio/stream-sessions` | Bearer token. Speech-only session. Returns a resume token, not the API key. |

## Session creation in plain language

Before the browser can stream microphone audio, it asks the backend to create a
session. The backend returns a session ID, a resume token, and the WebSocket URL.

## Current status

`POST /v1/sessions` requires the same bearer token as the audio routes and returns a random resume token. `development-token` is rejected. One live socket may hold that token. Do not put the token in a browser build or a log.

`/v1/audio/transcriptions` requires `SONIC_API_KEY`. `/health/live` can return 200 while `/health/ready` is false. Field details, error codes, and the local and Space deploy steps are in `hf/README.md` and [Speech recognition](../speech-recognition.md).
