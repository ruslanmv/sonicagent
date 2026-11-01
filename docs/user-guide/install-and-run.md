# Install and run

Use the voice image when you want Whisper and Piper. Use `make dev` when you want the mock API without downloading models.

## Requirements

- Python 3.11 or newer, for tests and the mock API.
- Node.js 20 or newer, for the web client tests.
- Docker, for the speech image.

## Get the code

```bash
git clone https://github.com/ruslanmv/sonicagent.git
cd sonicagent
```

## Speech image

```bash
cp hf/.env.example hf/.env
# Set SONIC_API_KEY in hf/.env. Use at least 16 characters locally.
docker compose -f hf/docker-compose.yml up --build
```

Local API: `http://127.0.0.1:8000`

Voice Studio: `http://127.0.0.1:8000/`

The container listens on `7860`. Compose publishes that port as `8000`. The first build downloads Whisper Tiny. Piper in this Compose file stays off until `SONIC_TTS_ENABLED=true`. The Hugging Face image turns synthesis on and downloads the voice mirror during the build. Details are in `hf/README.md`.

## Mock API

```bash
make install
make dev
```

| Service | URL |
| --- | --- |
| API | `http://localhost:8000` |
| OpenAPI | `http://localhost:8000/docs` |
| Live health | `http://localhost:8000/health/live` |
| Unfinished realtime page | `http://localhost:5173` |

`/health/live` means the process is up. `/health/ready` means Whisper has loaded. The mock API does not load it.

## Tests

```bash
make test
make lint
```

Some realtime modules are still skipped. Those skips are the unfinished gateway. They do not mean the batch speech tests failed.

Stop `make dev` with `Ctrl+C`. Stop Compose with `docker compose -f hf/docker-compose.yml down`.
