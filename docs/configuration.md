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

## Local example

Create a `.env` file from the example file:

```bash
cp .env.example .env
```

Then edit values carefully. Do not commit secrets, API keys, private audio, or
private transcripts.

## Beginner recommendation

For a first local test, keep the mock provider settings. Real model settings are
for later, after model files, checksums, and licenses are verified.
