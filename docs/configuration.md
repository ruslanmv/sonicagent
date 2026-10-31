# Configuration

Configuration controls how SonicAgent-RT starts, which providers it uses, and how
much work it accepts at one time.

## Where settings come from

The backend reads environment variables that start with `SONIC_`. For example,
`SONIC_PORT=8000` sets the API port.

Common settings:

| Setting | Default | Simple explanation |
| --- | --- | --- |
| `SONIC_HOST` | `0.0.0.0` | Network address the backend listens on. |
| `SONIC_PORT` | `8000` | Backend HTTP port. |
| `SONIC_ALLOWED_ORIGINS` | `http://localhost:5173` | Browser origins allowed during development. |
| `SONIC_LLM_PROVIDER` | `mock` | Text provider. `mock` is deterministic for tests. |
| `SONIC_MODEL_CACHE_DIR` | `~/.cache/sonicagent-rt` | Where downloaded model files should live. |
| `SONIC_STORE_AUDIO` | `false` | Whether to store audio. Keep disabled unless you have consent. |
| `SONIC_STORE_TRANSCRIPTS` | `false` | Whether to store transcripts. Keep disabled unless you have consent. |
| `SONIC_STT_MODEL` | `tiny` | Multilingual Whisper size. `tiny.en` is rejected. |
| `SONIC_STT_DEVICE` | `cpu` | `cpu`, `cuda`, `gpu`, or `auto`. CUDA is used only when a device exists. |
| `SONIC_STT_COMPUTE_TYPE` | `int8` | CTranslate2 compute type on CPU. |
| `SONIC_STT_LANGUAGE` | `auto` | Default language: `en`, `it`, or `auto`. |
| `SONIC_STT_ALLOW_DOWNLOAD` | `false` | Warmup may download weights only when this is true. |
| `SONIC_API_KEY` | empty | Bearer secret for `/v1/audio/*`. Required. Never commit it. |
| `SONIC_AUTH_MODE` | `development` | `token` or production requires a key of at least 24 characters. |
| `SONIC_MAX_AUDIO_SECONDS` | `15` | Decoded recording cap. |
| `SONIC_MAX_UPLOAD_BYTES` | `2097152` | Upload cap. |
| `SONIC_TTS_ENABLED` | `false` | Piper stays unavailable until this is true and voice files exist. |

## Local example

Create a `.env` file from the example file:

```bash
cp .env.example .env
```

Then edit values carefully. Do not commit secrets, API keys, private audio, or
private transcripts.

## Beginner recommendation

For a first voice test, use the `hf/` image and multilingual `tiny`. Keep `SONIC_STORE_AUDIO` and `SONIC_STORE_TRANSCRIPTS` false. The LLM provider can stay `mock` while you test transcription alone. Transcription does not call the LLM.
