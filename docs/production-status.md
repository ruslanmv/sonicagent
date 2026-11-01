# Production status

SonicAgent-RT is **not production-ready yet**.

This page is intentionally direct so users do not mistake a development checkout
for a deployable voice-assistant platform.

## Verified in the current implementation pass

These checks were run successfully in the development environment:

```bash
make install
python -m sonicagent_rt --help
python -c "import sonicagent_rt; print(sonicagent_rt.__version__)"
make test
make lint
make smoke
```

However, successful completion of these checks does not mean the full product is
ready. Some commands run with fake providers, and some tests still report known
scaffold skips.

## Known blockers

| Area | Status | Why it matters |
| --- | --- | --- |
| Runtime dependencies | Not fully installed in restricted environments | The backend cannot start without packages such as `fastapi` and `uvicorn`. |
| VAD endpointing | Incomplete | The server must reliably detect when a user starts and stops speaking. |
| STT batch API | Implemented for multilingual Tiny on CPU | Realtime streaming, GPU hosting, and a verified Space deployment are still open. |
| Piper batch WAV | Every voice in `ruslanmv/hp-piper-voices`, with female Companion and Secretary presets where a female speaker exists | Portuguese voices in that mirror are male and stay labeled male. Phrase-pipelined realtime playback is still open. |
| Barge-in | Incomplete | Users must be able to interrupt assistant speech safely. |
| Browser demo | Incomplete | The user interface still needs complete microphone, playback, reconnect, and status handling. |
| Model registry | Incomplete | Model checksums and attribution must be verified before release. |
| Security hardening | Incomplete | Authentication, origins, rate limits, and privacy controls need full review. |
| Test suite | Incomplete | Existing skipped scaffold tests must be replaced with meaningful coverage. |

## What is safe to do now

- Read the documentation.
- Run deterministic unit, contract, web, and fake-provider smoke checks.
- Develop and test isolated components.
- Use fake providers for demos that do not claim real-model performance.

## What not to do yet

- Do not expose the development server to the public internet.
- Do not process private customer audio or transcripts.
- Do not claim verified latency or production readiness.
- Do not commit model binaries, private audio, transcripts, local caches, or secrets.

## Release readiness checklist

Before a production release, the project needs:

- `make install`, `make run`, `make test`, `make lint`, and `make smoke` to pass
  from a clean checkout with documented dependencies.
- No placeholder-only skipped tests in required suites.
- Real-model model download and verification workflows.
- End-to-end browser and Python-client demos.
- Documented security, privacy, deployment, and rollback procedures.
- Benchmark reports with hardware, commit hash, provider versions, and honest
  latency numbers.
