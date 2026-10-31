# Errors

Speech endpoints use one JSON envelope:

```json
{"error": {"code": "unauthenticated", "message": "authentication is required", "request_id": "utt_123"}}
```

`request_id` is omitted when the caller did not send one and the failure happened before an id was assigned.

| Code | HTTP | When |
| --- | --- | --- |
| `unauthenticated` | 401 | Missing, empty, or placeholder bearer token. |
| `origin_denied` | 403 | `Origin` is present and not on the allowlist. |
| `voice_disabled` | 404 | `SONIC_VOICE_ENABLED=false`. |
| `invalid_request` | 400 | Missing fields or an illegal request id. |
| `unsupported_language` | 400 | Language outside `en`, `it`, and `auto`. |
| `unsupported_model` | 400 | English-only model, or a model other than the loaded one. |
| `unsupported_format` | 400 | Container type the decoder will not accept. |
| `audio_too_large` | 413 | Upload above `SONIC_MAX_UPLOAD_BYTES` (default 2 MiB). |
| `audio_too_long` | 413 | Decoded audio above `SONIC_MAX_AUDIO_SECONDS` (default 15). |
| `text_too_long` | 413 | TTS text above `SONIC_TTS_MAX_CHARS`. |
| `invalid_audio` | 422 | Empty file or a container that cannot be decoded. |
| `unsupported_codec` | 415 | A non-WAV upload when PyAV is not installed. |
| `duplicate_request` | 409 | The same `request_id` is already in flight. |
| `rate_limited` | 429 | The caller exceeded the sliding window. |
| `cancelled` | 408 | The client disconnected or cancellation won the race. |
| `timeout` | 504 | Inference exceeded its deadline. |
| `backend_warming` | 503 | The model is still loading. |
| `model_unavailable` | 503 | The library or checkpoint is missing. |
| `voice_unavailable` | 503 | Piper is disabled or the voice files are absent. |
| `inference_failed` | 500 | The engine raised an unexpected error. |

429 and 503 responses include `Retry-After`. Speech responses send `Cache-Control: no-store`. Error messages do not include the API key, audio bytes, or transcript text.
