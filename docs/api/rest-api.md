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

## Session creation in plain language

Before the browser can stream microphone audio, it asks the backend to create a
session. The backend returns a session ID, a resume token, and the WebSocket URL.

## Current status

Some REST endpoints are still development implementations. Do not expose them to
the public internet until authentication, origin checks, rate limits, and schema
tests are complete.
