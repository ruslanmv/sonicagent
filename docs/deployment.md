# Deployment

Deployment means running SonicAgent-RT somewhere other people or systems can use
it. The current repository is for development and testing, not production use.

## Local development

Use this while building or trying the app:

```bash
make install
make run
```

## Container development

A Docker Compose file is included for local experiments:

```bash
docker compose config
docker compose up --build
```

## Production requirements

Before production deployment, prepare:

- TLS/HTTPS in front of the API and WebSocket.
- Real authentication and short-lived session tokens.
- An allowlist for browser origins.
- Rate limits and session concurrency limits.
- A persistent model cache outside Git.
- Monitoring for errors, latency, and resource usage.
- A rollback plan.
- A privacy review for audio and transcript handling.

## Do not deploy yet if

- `make run` cannot start the backend.
- Tests still show placeholder-only skips.
- Runtime dependencies are missing.
- Model checksums and licenses are not verified.
