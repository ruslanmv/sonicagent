# Deployment

Two hosts run the speech API today. Neither one is a production service level.

## Local voice image

```bash
docker compose -f hf/docker-compose.yml up --build
```

The image listens on container port `7860` and Compose publishes `http://127.0.0.1:8000`. Voice Studio is `/`. Readiness is `/health/ready`, after Whisper has loaded. Live health is only process liveness.

Windows, secrets, and rollback are in `hf/README.md`.

## Hugging Face Space

`hf/scripts/deploy-space.sh` stages this same image for the existing Space `ruslanmv/SonicAgent`. The Space is a remote CPU. It can sleep. It is not on-device inference and it is not an offline Quest mode.

Put `SONIC_API_KEY` in a Space secret. Do not bake it into the image or the Voice Studio bundle.

The root `docker compose up` file starts the mock API and the unfinished web client. It does not start Whisper.

## Before a production deployment

- TLS in front of the API.
- Real authentication. The development token is rejected when auth mode is `token`.
- An origin allowlist for any browser that calls the API with cookies.
- Rate limits and a concurrency cap. The public demo already has its own caps.
- A persistent model cache outside Git.
- Voice checksums filled in. Piper hashes in the registry are still `TODO`.
- Monitoring that records timings and error codes, not transcript text.
- A rollback plan.

## Do not treat these as production

- A sleeping CPU Basic Space.
- `/health/live` used as a model check.
- The WebSocket path. It does not run a voice turn.
- A latency number from a different machine than the one you measured.
