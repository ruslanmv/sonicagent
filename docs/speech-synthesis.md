# Speech synthesis

Batch text-to-speech is implemented with Piper. The realtime turn speaks a finished phrase as PCM frames before the rest of the reply when Piper is ready. A cancelled turn sets `clear_audio` so the client drops queued playback.

## What runs

- Package: `piper-tts` 1.8.0, imported as `piper`.
- Voices: every entry in `model_registry/voices.json`, from `ruslanmv/hp-piper-voices`.
- Files: `{cache}/tts/{id}.onnx` and `{id}.onnx.json`. The image downloads them at build time.
- Presets: Companion (slower, softer) and Secretary (a little faster, steadier) where a female speaker exists. Other speakers keep their published gender. Portuguese in this mirror is male.
- Synthesis settings travel with the voice: `length_scale`, `noise_scale`, `noise_w_scale`, and `speaker_id`.
- `ready` is true when TTS is enabled, Piper imports, and at least one voice file is on disk. Warmup loads the default voice. Other voices load on first use.

Source: `src/sonicagent_rt/tts/piper_process.py` and `src/sonicagent_rt/api/routes/audio.py`.

## HTTP API

| Endpoint | Auth | Meaning |
| --- | --- | --- |
| `POST /v1/audio/speech` | Bearer | JSON text and voice id in, `audio/wav` out. |
| `GET /v1/audio/capabilities` | Bearer | Includes the installed voice ids. |

The voice image sets `SONIC_TTS_ENABLED=true`. Local Compose leaves it false until you set it. The public demo synthesizes only when `SONIC_PUBLIC_DEMO_TTS_ENABLED=true`, and that path caps the text at 180 characters.

Some upstream configs say `PhonemeType.ESPEAK`. Piper 1.8 expects `espeak`. The loader rewrites that before synthesis. The Spanish Mexico Ald voice needs that rewrite.

## Privacy

Synthesis does not store the text or the WAV unless `SONIC_STORE_AUDIO` is turned on. It is off by default.
