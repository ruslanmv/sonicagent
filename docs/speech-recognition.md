# Speech recognition

Batch speech-to-text is implemented with `faster-whisper` and CTranslate2. Realtime WebSocket transcription is not implemented.

## What runs

- Provider: `SONIC_STT_PROVIDER=faster-whisper`.
- Default model: multilingual `tiny`, public id `whisper-tiny`.
- Device: CPU INT8 unless CUDA is actually present and requested.
- Languages: English, Spanish, French, German, Italian, and Portuguese. `auto` leaves detection to Whisper. `tiny.en` and any other `*.en` id are rejected.
- Input: WAV through the standard library, and WebM, Opus, Ogg, MP3, or MP4 through PyAV when `av` is installed. Audio is converted to mono float32 at 16 kHz.
- One loaded `WhisperModel` is reused. Requests do not download weights.

Source: `src/sonicagent_rt/stt/faster_whisper.py`, `src/sonicagent_rt/audio/decode.py`, and `src/sonicagent_rt/api/routes/audio.py`.

## HTTP API

| Endpoint | Auth | Meaning |
| --- | --- | --- |
| `GET /health/live` | No | The process is up. This is not model readiness. |
| `GET /health/ready` | No | `ready: true` only after Whisper has loaded. |
| `GET /v1/audio/capabilities` | Bearer | Installed, loading, ready, and unsupported features. |
| `POST /v1/audio/transcriptions` | Bearer | One utterance in, one JSON transcript out. |

Silence returns an empty `text` when the engine is available. Corrupt audio, oversize uploads, and a missing model return errors. The handler never invents a sentence.

## Privacy

`SONIC_STORE_AUDIO` and `SONIC_STORE_TRANSCRIPTS` default to false. Transcript text is not a log field. Limits default to 15 seconds, 2 MiB, two concurrent inferences, and a per-token rate limit.

## Tests

Unit tests fake the engine. `tests/integration/test_batch_transcription.py` loads the pinned Tiny checkpoint and transcribes the English and Italian fixtures. That test is marked `integration` and is not part of the default unit job.

Deployment of this API is documented in `hf/README.md`.
