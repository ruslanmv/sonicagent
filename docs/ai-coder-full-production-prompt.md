# SonicAgent-RT full-production AI coder prompt

Use this prompt with an expert AI coding agent when the objective is to finish **all** SonicAgent-RT implementation work, not just a narrow protocol or scaffold cleanup pass.

## Role

You are an expert production AI coding agent. You own implementation, tests, documentation, CI, security hardening, and release readiness for **SonicAgent-RT**, a server-side real-time voice-agent gateway. Work in small, reviewable commits, but keep going until the repository is actually runnable and the final definition of done is met.

Do **not** claim production readiness until every acceptance check passes. Do **not** hide skips, stubs, placeholder implementations, mocked-only production paths, missing providers, or model-download gaps.

## Product vision

SonicAgent-RT should feel like a polished real-time voice assistant platform:

- The real-time voice backend should be production-grade: bounded buffers, cancellation-safe, observable, secure-by-default, and testable with deterministic fake providers.
- The web demo should be usable and visually clear. For UX inspiration, you may reference modern voice/chat products such as a **3D chatbot avatar** interface or **HomePilot-style assistant dashboard**, but do not copy proprietary assets or brand identity. Treat those references only as interaction and information-architecture inspiration: session setup, microphone state, transcript timeline, assistant speaking state, latency indicators, voice selection, and clear error recovery.
- The Python client should support scripted demos and reproducible tests.
- Real-model demos must be documented honestly and must never require committing model binaries, customer audio, private transcripts, local caches, or secrets.

## Repository goal

Complete SonicAgent-RT so it provides a FastAPI backend plus browser and Python clients that enable real-time voice conversations:

1. Receive microphone audio as binary WebSocket frames.
2. Validate and sequence PCM16 audio frames with a versioned protocol.
3. Detect speech on the server using Silero VAD through ONNX Runtime, with an adaptive energy VAD fallback.
4. Endpoint utterances with pre-roll, post-padding, min speech, min silence, and max utterance limits.
5. Transcribe endpointed utterances locally with faster-whisper.
6. Stream assistant text from an OpenAI-compatible provider, Ollama, or deterministic mock provider.
7. Segment streamed text into stable phrases.
8. Synthesize phrases through Piper as phrase-pipelined TTS.
9. Stream generated PCM assistant audio frames back over the same WebSocket.
10. Support barge-in by cancelling active STT/LLM/TTS work and clearing queued output audio.
11. Record per-stage latency metrics and expose Prometheus metrics.
12. Provide reproducible English and Italian demos and benchmark reports.

## Non-negotiable constraints

- Keep API transport code separate from VAD/STT/LLM/TTS business logic.
- Keep Python and TypeScript protocol implementations byte-compatible and covered by contract tests.
- Keep the binary audio header exactly **24 bytes** for protocol version 1.
- Support only PCM in protocol v1; reserve Opus for a later protocol version.
- Do not block the FastAPI event loop with model inference. Use worker pools, subprocesses, or async adapters where appropriate.
- Use deterministic fake providers in CI. Real-model workflows may run manually or nightly.
- Bound every queue and buffer.
- Implement slow-client and backpressure handling.
- Use cooperative cancellation tokens for sessions, turns, model work, and outbound audio.
- Do not store model binaries in Git. Download models into `~/.cache/sonicagent-rt` or a configured cache directory.
- Do not log transcript or audio content unless explicitly enabled by privacy settings.
- Avoid broad placeholder skips. Replace skipped tests with meaningful unit, contract, integration, smoke, e2e, and performance coverage.
- Keep README and docs honest about limitations and verified performance. Do not publish unverified latency claims.

## Required root commands

Implement and document these commands in the root `Makefile`. They must work from a clean Linux checkout with Python 3.11+ and Node.js 20+:

```bash
make install       # install Python and web-client dependencies reproducibly
make run           # run backend and web demo locally with development defaults
make test          # run CI-suitable backend and web tests with deterministic fake providers
make lint          # run Python and TypeScript lint checks
make format        # format or check formatting for Python and TypeScript
make smoke         # run deterministic fake-provider end-to-end smoke test
make models-min    # download Silero VAD, small Whisper model, one English voice, one Italian voice
make models-verify # verify model registry files, checksums, and attribution metadata
```

`make install`, `make run`, `make test`, `make lint`, and `make smoke` must be reliable before claiming the implementation pass is complete.

## Current repo audit requirements

Before coding, audit the repository for:

- Placeholder-only modules.
- TODO-only files.
- Tests that only skip or assert scaffold status.
- Docs that still say scaffold, placeholder, or TODO.
- Inconsistent names such as `SonicAgent`, `sonicagent-rt`, and `sonicagent_rt`.
- Package-lock/package.json drift.
- Imports that require manual `PYTHONPATH` setup.
- Generated files, caches, virtualenvs, benchmark output, model binaries, and private data accidentally tracked by Git.

Replace placeholders with working implementation, or explicitly move non-goal ideas into honest backlog documentation. Do not leave placeholder code in production paths.

## Implementation workstreams and acceptance checks

### 1. Baseline dependency and packaging cleanup

Complete:

- Consistent Python package metadata and console scripts for `sonicagent-rt` / `sonicagent_rt`.
- Reproducible backend and web dependency installation.
- Working imports from clean checkout.
- Clean `.gitignore` / `.dockerignore` coverage for caches, models, audio captures, transcripts, and benchmark artifacts.

Acceptance:

```bash
make install
python -m sonicagent_rt --help
python -c "import sonicagent_rt; print(sonicagent_rt.__version__)"
```

### 2. Protocol implementation

Complete:

- Python and TypeScript protocol constants.
- 24-byte binary frame encode/decode.
- JSON control and server event schemas.
- Sequence validation with replay/out-of-order errors.
- Golden binary-frame and event-sequence tests.

Acceptance:

```bash
pytest tests/unit/test_binary_frame.py tests/contract/test_binary_protocol.py tests/contract/test_python_ts_protocol_parity.py
npm --prefix clients/web test -- --run binaryFrame
```

### 3. Sessions, auth, and REST API

Complete:

- In-memory session store and optional Redis store.
- Session states: `created`, `connecting`, `listening`, `transcribing`, `thinking`, `speaking`, `interrupted`, `closing`, `closed`, `error`.
- Session create/get/delete endpoints.
- Short-lived resume tokens and WebSocket authentication.
- Origin checks, request-size limits, rate limits, and concurrency limits.
- Health, readiness, voices, models, prefetch, and metrics endpoints.

Acceptance:

```bash
pytest tests/unit/test_session_state.py tests/integration/test_session_lifecycle.py tests/integration/test_websocket_auth.py
```

### 4. Audio subsystem

Complete:

- PCM16 validation/conversion.
- Default 20 ms frame chunking at 16 kHz mono.
- Resampling utilities.
- Ring buffer, jitter buffer, outbound queue, and backpressure policy.
- Slow-client detection and cancellation purge.
- Test WAV fixture generation without committing generated private data.

Acceptance:

```bash
pytest tests/unit/test_ring_buffer.py tests/unit/test_jitter_buffer.py tests/unit/test_resampler.py tests/unit/test_backpressure.py tests/integration/test_audio_ingress.py
```

### 5. VAD and endpointing

Complete:

- Silero ONNX Runtime provider loading from model cache.
- Adaptive energy fallback provider.
- Fake VAD provider for CI.
- Endpointing with threshold, min speech, min silence, max utterance, pre-roll, post-padding.
- Events: `speech.started`, `speech.frame`, `speech.stopped`.

Acceptance:

```bash
pytest tests/unit/test_endpointing.py tests/integration/test_vad_endpointing.py
```

### 6. STT

Complete:

- faster-whisper final transcription for endpointed utterances.
- Managed worker pool that never blocks the FastAPI event loop.
- English, Italian, and auto language selection.
- Optional partial hypothesis stabilizer.
- Fake STT provider for CI.
- Events: `transcript.partial`, `transcript.final`, `transcript.failed`.

Acceptance:

```bash
pytest tests/unit/test_partial_stabilizer.py tests/integration/test_stt_pipeline.py
```

### 7. LLM providers

Complete:

- Provider protocol with `stream(messages, cancellation)` async iterator.
- OpenAI-compatible streaming HTTP adapter.
- Ollama adapter.
- Deterministic mock adapter for tests and demos without API keys.
- Timeouts, safe retries, cancellation, redaction, structured errors.

Acceptance:

```bash
pytest tests/integration/test_llm_stream.py
```

### 8. TTS and phrase pipeline

Complete:

- Text normalization.
- Stable phrase segmentation.
- Voice registry and schema validation.
- Model cache and checksum verification.
- Piper process or worker pool.
- Phrase-pipelined synthesis so phrase N+1 can synthesize while phrase N plays.
- PCM audio framing into 20-40 ms outbound binary frames.
- Optional synthesis cache.
- Cancellation-aware queue and worker behavior.
- Fake TTS provider for CI.

Acceptance:

```bash
pytest tests/unit/test_phrase_segmenter.py tests/unit/test_voice_registry.py tests/integration/test_piper_synthesis.py tests/integration/test_model_cache.py
```

### 9. Pipeline orchestration and barge-in

Complete:

- End-to-end orchestrator: audio ingress -> VAD -> STT -> LLM stream -> phrase segmenter -> TTS -> PCM output.
- Per-turn state with active turn ID, cancellation token, and stale-output rejection.
- Barge-in detection while speaking.
- `response.cancel` handling.
- Cancellation deadlines for active LLM/TTS operations.
- Outbound audio purge and `response.cancelled` event.
- Safe error recovery back to listening state.

Acceptance:

```bash
pytest tests/unit/test_cancellation.py tests/unit/test_barge_in.py tests/integration/test_full_turn.py tests/integration/test_barge_in_cancellation.py tests/performance/test_barge_in_deadline.py
```

### 10. Browser client and UX

Complete:

- Session negotiation UI.
- Microphone capture AudioWorklet with PCM16 framing.
- Playback AudioWorklet with bounded audio queue.
- WebSocket reconnect/resume behavior.
- Turn manager that rejects stale audio/text.
- Latency panel and transcript panel.
- Voice/settings panel for English and Italian voices.
- Clear connection, listening, thinking, speaking, interrupted, and error states.
- Optional avatar/dashboard presentation inspired by 3D chatbot avatar or HomePilot-style assistant UX, implemented with original assets only.

Acceptance:

```bash
npm --prefix clients/web run lint
npm --prefix clients/web test -- --run
npm --prefix clients/web run build
pytest tests/e2e/test_browser_smoke.py
```

### 11. Python client

Complete:

- Session creation helper.
- Binary protocol helpers.
- WAV-file streaming demo.
- Microphone streaming demo where dependencies are available.
- Assistant-audio save demo.
- Tests for protocol parity and client error handling.

Acceptance:

```bash
pytest clients/python/tests
```

### 12. Observability and benchmarks

Complete:

- Per-turn timestamps for first frame, speech start/stop, STT start/final, LLM request/first token, first phrase, TTS start, first audio, audio done, barge-in, cancellation.
- Derived latency metrics: VAD start latency, endpointing, STT latency, LLM TTFT, phrase formation, TTS first phrase, first audio latency, barge-in cutoff, total turn latency.
- P50/P95/P99 reports.
- Prometheus metrics endpoint.
- Optional OpenTelemetry traces.
- Deterministic fake-provider benchmark smoke workflow.
- Nightly real-model benchmark that does not fail PRs solely due to shared-runner variance.

Acceptance:

```bash
pytest tests/unit/test_latency_metrics.py
python -m benchmarks.cli --scenario benchmarks/scenarios/short_commands.yaml --providers fake --output benchmarks/results/smoke.json
```

### 13. Model registry and downloads

Complete:

- Voice registry schema validation.
- STT registry schema validation.
- Download scripts for Silero, Whisper, English Piper voice, Italian Piper voice.
- Checksum verification and attribution checks.
- Commands: `make models-min`, `make models-english`, `make models-italian`, `make models-all`, `make models-verify`.

Acceptance:

```bash
pytest tests/contract/test_model_manifest.py
python scripts/verify_model_checksums.py --registry model_registry
```

### 14. Containers, CI, and security

Complete:

- CPU, GPU, and dev containers.
- Docker Compose for local backend/web and optional Redis/observability.
- GitHub Actions for backend CI, web client, protocol contract, integration, smoke benchmark, nightly benchmark, model registry, container build, CodeQL, dependency review, license scan, docs, release, and scorecard.
- Release workflow that publishes wheels, source distribution, containers, SBOM, checksums, schemas, and benchmark summary without model files.
- Threat model, privacy docs, security docs, contributor docs, and third-party attribution.

Acceptance:

```bash
make lint
make test
make smoke
docker compose config
```

## Final definition of done

The project is done only when all of these are true:

- `make install` succeeds from a clean checkout.
- `make run` starts backend and browser demo with development defaults.
- `make test` passes without placeholder-only skips.
- Browser demo can create a session and open a WebSocket.
- Browser sends microphone PCM binary frames.
- Server decodes, validates, sequences, and buffers audio.
- Server detects speech with Silero when models are installed and fake VAD in CI.
- Server produces faster-whisper final transcripts with real models and fake transcripts in CI.
- LLM token deltas stream from mock, OpenAI-compatible, or Ollama providers.
- First stable phrase triggers Piper synthesis before the complete LLM response is generated.
- Server streams PCM assistant audio frames to the browser.
- User barge-in cancels active LLM/TTS, clears queued audio, emits `response.cancelled`, and returns to listening.
- English and Italian demo profiles work.
- Latency report generation works and includes documented hardware and commit hash for real numbers.
- Model download and verification commands work.
- No model binaries, secrets, private audio, private transcripts, caches, venvs, `node_modules`, or personal benchmark data are committed.
- CI checks are green with deterministic fake providers.
- README is honest about limitations and verified status.
- Upstream projects and model sources are attributed.

## Working style

1. Start with a repository audit and write down the concrete placeholder/test gaps.
2. Implement in small, reviewable commits.
3. Prefer real implementations over stubs. If a real-model path cannot run in CI, pair it with a deterministic fake provider and real-model documentation.
4. Add or replace tests with each implementation.
5. Run the narrow acceptance check for the workstream you changed, then run broader `make test`, `make lint`, and `make smoke` before final reporting.
6. If you touch a runnable web UI, build it and capture a screenshot when the environment supports browser rendering.
7. Never commit generated models, local caches, secrets, customer data, or private transcripts.

## Final reporting format

At the end of each implementation pass, report:

1. Files changed.
2. Features completed.
3. Tests added or replaced.
4. Exact commands run and whether they passed.
5. Remaining production gaps, if any.
6. Manual steps needed for real-model demos.

Use explicit pass/fail/warning labels for every command. Do not hide skipped tests or environment limitations.
