# SonicAgent

SonicAgent is a speech service. It transcribes an utterance and returns a WAV. The same API runs in the `hf/` image on your machine and on the Hugging Face Space `ruslanmv/SonicAgent`.

The realtime path (WebSocket audio, voice activity detection, barge-in, and a streaming language model) is designed and not running. See [Production status](production-status.md).

## Who is this documentation for?

- **Operators** who install the voice image or the Space.
- **Product engineers** who call the batch HTTP API.
- **Developers** who need the protocol, the tests, and the remaining realtime work.

## Start here

1. Read [What this service does](user-guide/what-is-sonicagent.md).
2. Follow [Install and run](user-guide/install-and-run.md) for the voice image.
3. Open [Voice Studio](user-guide/browser-demo.md).
4. If something fails, check [Troubleshooting](troubleshooting.md).

## Checks

```bash
make install
make test
make lint
```

`make dev` starts the mock API on port 8000. It does not load Whisper or Piper. The speech service is `docker compose -f hf/docker-compose.yml up --build`.
