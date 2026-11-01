# OllaBridge Cloud voice contract

This document is the contract for connecting the 3D Avatar to SonicAgent. The SonicAgent service in this repository implements the voice API. OllaBridge Cloud routing is **not** implemented in this change and must not be confused with the existing Hugging Face chat provider.

## What already exists

OllaBridge Cloud can already route **chat completions** to Hugging Face or to a paired PC running Ollama. That chat path does not transcribe audio. Its Hugging Face provider reads `HF_TOKEN` and, when disabled, returns a deterministic text stub. Do not send microphone audio to that chat API and do not treat the stub as a transcript.

## Modes

OllaBridge should grow one voice setting, separate from the chat model:

| Mode | Behavior |
| --- | --- |
| `local` | Relay a bounded utterance to the user's paired OllaBridge, which calls SonicAgent on that PC. The PC must be on. |
| `huggingface` | Call the SonicAgent Space directly over HTTPS. The PC can be off. |
| `disabled` | Do not advertise speech. Typed chat still works. |

`huggingface` mode must not require a connected device relay. `local` mode must keep using the owner-scoped relay and must not become an open proxy.

## SonicAgent endpoints

Base URL examples:

- Local Docker: `http://127.0.0.1:8000`
- Hugging Face: the Space app URL shown after a successful build of `ruslanmv/SonicAgent`. This repository does not hard-code that hostname.

```text
GET  /health/live
GET  /health/ready
GET  /v1/audio/capabilities
POST /v1/audio/transcriptions
POST /v1/audio/speech
```

`/health/live` returning 200 only means the process is listening. Call `/health/ready` or capabilities and require `stt.ready == true` before accepting a conversation turn. A sleeping or still-loading Space is `ready: false` with a reason such as `model-not-loaded` or `model-loading`. Surface that as temporary unavailability. Do not invent a transcript.

### Authentication

OllaBridge stores `SONIC_API_KEY` as a server-side secret and sends:

```text
Authorization: Bearer <SONIC_API_KEY>
```

The Avatar browser must never receive this value. The browser authenticates to OllaBridge Cloud with the user's existing session.

Production SonicAgent (`SONIC_ENVIRONMENT=production` or `SONIC_AUTH_MODE=token`) rejects empty keys, known placeholders such as `development-token`, and keys shorter than 24 characters.

### Transcription

`multipart/form-data` fields: `file` (or `audio`), `language` (`en`, `it`, or `auto`), optional `model`, optional `request_id`.

Success JSON:

```json
{
  "text": "Hello. Can you help me?",
  "language": "en",
  "model": "whisper-tiny",
  "is_final": true,
  "request_id": "utt_123",
  "duration_ms": 2854
}
```

`duration_ms` is the decoded audio length. Empty `text` means no speech was detected. It is not a placeholder success.

Stable error envelope:

```json
{"error": {"code": "unauthenticated", "message": "authentication is required", "request_id": "utt_123"}}
```

Codes include `unauthenticated`, `origin_denied`, `unsupported_codec`, `unsupported_language`, `unsupported_model`, `audio_too_large`, `audio_too_long`, `invalid_audio`, `rate_limited`, `duplicate_request`, `timeout`, `backend_warming`, `model_unavailable`, `voice_unavailable`, `cancelled`, and `inference_failed`.

Limits to enforce again at OllaBridge, before base64 expansion: 15 seconds, 2 MiB encoded audio, one in-flight request id per user.

### Speech synthesis

`POST /v1/audio/speech` with JSON `{"text", "voice", "language", "format": "wav"}` returns `audio/wav` only when Piper and the voice files are installed and `SONIC_TTS_ENABLED=true`. Otherwise the service returns `voice_unavailable`. The Avatar's existing local Piper remains the default speaker.

### PC-off chat

SonicAgent does not generate the assistant reply. For Quest use with the PC powered off, OllaBridge Cloud also needs an online LLM that is not Ollama-on-Windows. If speech-to-text succeeds and the LLM is unavailable, show that distinction. Do not hide it inside the transcription response.

### Suggested cloud environment

```text
OLLAMBRIDGE_VOICE_MODE=huggingface
OLLAMBRIDGE_VOICE_BASE_URL=https://<space-app-host>
OLLAMBRIDGE_VOICE_API_KEY=<server-side SonicAgent key>
OLLAMBRIDGE_VOICE_TIMEOUT_SEC=60
```

These names are a proposal for the OllaBridge Cloud PR. They are not read by SonicAgent.

Realtime WebSocket audio is not part of this API. Do not stream 20 ms PCM frames through the JSON device relay.
