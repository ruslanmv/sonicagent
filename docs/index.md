# SonicAgent-RT

SonicAgent-RT is a server application for building real-time voice assistants.
In plain language, it is the middle layer between a microphone, speech-to-text,
an AI text model, text-to-speech, and a browser or Python client.

!!! warning "Current readiness"
    SonicAgent-RT is **not production-ready yet**. The repository still has known
    scaffolded tests and missing real-model runtime dependencies in some
    environments. See [Production status](production-status.md) before using it
    outside local development.

## Who is this documentation for?

- **Non-expert users** who want to understand what the app does and how to try it.
- **Operators** who need to install, configure, and troubleshoot the service.
- **Developers** who need protocol details, architecture notes, and test commands.

## Start here

1. Read [What this app does](user-guide/what-is-sonicagent.md).
2. Follow [Install and run](user-guide/install-and-run.md).
3. Open the [Browser demo guide](user-guide/browser-demo.md).
4. If something fails, check [Troubleshooting basics](troubleshooting.md).

## The short version

```bash
make install
make test
make smoke
make run
```

What those commands mean:

| Command | Purpose |
| --- | --- |
| `make install` | Installs the local Python package and web-client dependencies. |
| `make test` | Runs deterministic backend and web tests. |
| `make smoke` | Runs a fake-provider smoke benchmark. |
| `make run` | Starts the backend and browser demo for local use. |

If `make run` says `uvicorn is not installed`, install the Python runtime
dependencies from an approved package mirror before starting the backend.
