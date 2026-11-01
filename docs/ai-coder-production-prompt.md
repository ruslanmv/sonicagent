# AI Coder Production Prompt for SonicAgent-RT

Use this prompt for the remaining realtime gateway. Batch Whisper, batch Piper, Voice Studio, and the `hf/` image already run. Do not replace them with stubs. The expected outcome is a working realtime repo where `make install`, `make run`, and `make test` succeed from a clean checkout.

## Role

You are an expert production AI coding agent. You own implementation, tests, documentation, and CI hardening for **SonicAgent-RT**, a server-side real-time voice-agent gateway.

Work in small, reviewable commits. Do not claim production readiness until all acceptance criteria in this prompt pass. Do not commit secrets, generated model binaries, customer audio, private transcripts, local caches, virtual environments, `node_modules`, or benchmark data containing personal information.

## Repository goal

SonicAgent-RT must provide a FastAPI backend and browser/Python clients that enable real-time voice conversations:

1. Receive microphone audio as binary WebSocket frames.
2. Validate and sequence PCM16 audio frames with a versioned protocol.
3. Detect speech on the server using Silero VAD through ONNX Runtime, with an adaptive energy VAD fallback.
4. Endpoint utterances with pre-roll, post-padding, min speech/silence, and max utterance limits.
5. Transcribe endpointed utterances locally with faster-whisper.
6. Stream assistant text from an OpenAI-compatible LLM provider, Ollama, or deterministic mock provider.
7. Segment streamed text into stable phrases.
8. Synthesize phrases through Piper as phrase-pipelined TTS.
9. Stream generated PCM audio frames back over the same WebSocket.
10. Support barge-in by cancelling active STT/LLM/TTS work and clearing queued audio.
11. Record per-stage latency metrics and expose Prometheus metrics.
12. Provide reproducible English and Italian demos and benchmark reports.

## Non-negotiable production constraints

- Keep API transport code separate from VAD/STT/LLM/TTS business logic.
- Keep Python and TypeScript protocol implementations byte-compatible and covered by contract tests.
- Keep the binary audio header exactly 24 bytes for protocol version 1.
- Support only PCM in v1; reserve Opus for a later protocol version.
- Do not block the FastAPI event loop with model inference; use worker pools/subprocesses for STT and TTS.
- Use deterministic fake providers in CI; real-model workflows may run nightly or manually.
- Bound every queue and buffer. Implement slow-client and backpressure handling.
- Use cooperative cancellation tokens for turns, model work, and outbound audio.
- Do not store model binaries in Git. Download models into `~/.cache/sonicagent-rt` or a configured cache directory.
- Do not log transcript or audio content unless explicitly enabled by privacy settings.
- Avoid broad placeholder skips. Replace skipped tests with meaningful unit, contract, integration, and smoke coverage.

## Required developer commands

Implement and document these commands in the root `Makefile`:

```bash
make install      # install Python and web-client dependencies reproducibly
make run          # run backend and web demo locally with development defaults
make test         # run backend unit/contract tests and web tests suitable for CI
make lint         # run Python and TypeScript lint checks
make format       # format/check formatting for Python and TypeScript
make smoke        # run a deterministic fake-provider end-to-end smoke test
make models-min   # download Silero VAD, a small Whisper model, one English voice, one Italian voice
make models-verify
```

`make install`, `make run`, and `make test` are the minimum required commands for this task. They must work from a clean checkout on Linux with Python 3.11+ and Node.js 20+.

## Implementation plan

### 1. Baseline cleanup and dependency reproducibility

- Audit all placeholder modules and TODO-only files.
- Replace placeholder tests that only skip with actionable tests.
- Ensure `pyproject.toml`, lockfiles, package names, console scripts, and README refer consistently to `sonicagent-rt` / `sonicagent_rt`.
- Ensure web `package.json` and `package-lock.json` are synchronized.
- Ensure `make install` installs backend and web dependencies without requiring external secrets.
- Ensure imports work without manually exporting `PYTHONPATH`.

### 2. Protocol implementation

Implement and test:

- `protocol/constants.py` and `clients/web/src/protocol/constants.ts` with identical event names, message types, codecs, flags, and protocol version.
- `protocol/binary_frame.py` and `clients/web/src/protocol/binaryFrame.ts` for 24-byte header encode/decode.
- JSON control/server event schemas and validation.
- Sequence validation and replay/out-of-order error handling.
- Golden frame and event-sequence tests.

Acceptance checks:

```bash
pytest tests/unit/test_binary_frame.py tests/contract/test_binary_protocol.py tests/contract/test_python_ts_protocol_parity.py
npm --prefix clients/web test -- --run binaryFrame
```

### 3. Sessions, auth, and REST API

Implement:

- In-memory session store with optional Redis implementation.
- Session states: `created`, `connecting`, `listening`, `transcribing`, `thinking`, `speaking`, `interrupted`, `closing`, `closed`, `error`.
- Session creation, get, delete endpoints.
- Short-lived resume tokens and WebSocket authentication.
- Origin checks, request-size limits, rate limits, and session concurrency limits.
- Health, readiness, voice/model discovery, prefetch, and metrics endpoints.

Acceptance checks:

```bash
pytest tests/unit/test_session_state.py tests/integration/test_session_lifecycle.py tests/integration/test_websocket_auth.py
```

### 4. Audio subsystem

Implement:

- PCM16 validation and conversion.
- 20 ms frame chunking at 16 kHz mono by default.
- Resampling utilities.
- Ring buffer, jitter buffer, outbound queue, and backpressure policies.
- Slow-client detection and output queue purge on cancellation.
- WAV fixture generation for tests without committing generated output outside allowed fixtures.

Acceptance checks:

```bash
pytest tests/unit/test_ring_buffer.py tests/unit/test_jitter_buffer.py tests/unit/test_resampler.py tests/unit/test_backpressure.py tests/integration/test_audio_ingress.py
```

### 5. VAD and endpointing

Implement:

- Silero ONNX Runtime provider loading from configured model cache.
- Adaptive RMS/energy fallback provider.
- Endpointing with threshold, min speech, min silence, max utterance, pre-roll, and post-padding.
- Events: `speech.started`, `speech.frame`, `speech.stopped`.
- Fake VAD provider for CI.

Acceptance checks:

```bash
pytest tests/unit/test_endpointing.py tests/integration/test_vad_endpointing.py
```

### 6. STT

Implement:

- faster-whisper final transcription for endpointed utterances.
- Managed worker pool so inference does not block the event loop.
- Language selection for English, Italian, and auto detection.
- Optional rolling-window partial hypothesis stabilizer.
- Events: `transcript.partial`, `transcript.final`, `transcript.failed`.
- Fake STT provider for CI.

Acceptance checks:

```bash
pytest tests/unit/test_partial_stabilizer.py tests/integration/test_stt_pipeline.py
```

### 7. LLM providers

Implement:

- Provider protocol with `stream(messages, cancellation)` async iterator.
- OpenAI-compatible streaming HTTP adapter.
- Ollama adapter.
- Deterministic mock adapter for tests and demos without API keys.
- Timeouts, retries where safe, cancellation, redaction, and structured errors.

Acceptance checks:

```bash
pytest tests/integration/test_llm_stream.py
```

### 8. TTS and phrase pipeline

Implement:

- Text normalization.
- Stable phrase segmentation.
- Voice registry and schema validation.
- Model cache and checksum verification.
- Piper process/worker pool.
- Phrase-pipelined synthesis where phrase N+1 can synthesize while phrase N plays.
- PCM audio framing into 20-40 ms outbound binary frames.
- Optional synthesis cache.
- Cancellation-aware queue and worker behavior.
- Fake TTS provider for CI.

Acceptance checks:

```bash
pytest tests/unit/test_phrase_segmenter.py tests/unit/test_voice_registry.py tests/integration/test_piper_synthesis.py tests/integration/test_model_cache.py
```

### 9. Pipeline orchestration and barge-in

Implement:

- End-to-end orchestrator: audio ingress -> VAD -> STT -> LLM stream -> phrase segmenter -> TTS -> PCM output.
- Per-turn state with active turn ID, cancellation token, and stale-output rejection.
- Barge-in detection while speaking.
- `response.cancel` handling.
- Cancellation of active LLM and TTS operations within configured deadlines.
- Outbound audio purge and `response.cancelled` event.
- Error recovery that returns the session to listening when safe.

Acceptance checks:

```bash
pytest tests/unit/test_cancellation.py tests/unit/test_barge_in.py tests/integration/test_full_turn.py tests/integration/test_barge_in_cancellation.py tests/performance/test_barge_in_deadline.py
```

### 10. Browser client

Implement:

- Session negotiation UI.
- Microphone capture AudioWorklet with PCM16 framing.
- Playback AudioWorklet and bounded audio queue.
- WebSocket reconnect/resume behavior.
- Turn manager that rejects stale audio/text.
- Latency panel and transcript panel.
- Voice/settings panel with English and Italian voices.
- TypeScript protocol parity with Python.

Acceptance checks:

```bash
npm --prefix clients/web run lint
npm --prefix clients/web test -- --run
npm --prefix clients/web run build
pytest tests/e2e/test_browser_smoke.py
```

### 11. Observability and benchmarks

Implement:

- Per-turn timestamps: first frame, speech start/stop, STT start/final, LLM requested/first token, first phrase, TTS start, first audio, audio done, barge-in, cancellation.
- Derived metrics: VAD start latency, endpointing, STT latency, LLM TTFT, phrase formation, TTS first phrase, first audio latency, barge-in cutoff, total turn latency.
- P50/P95/P99 reports.
- Prometheus metrics endpoint.
- Optional OpenTelemetry traces.
- Deterministic benchmark smoke workflow with fake providers.
- Real-model nightly benchmark that never fails PRs solely due to shared-runner variance.

Acceptance checks:

```bash
pytest tests/unit/test_latency_metrics.py
python -m benchmarks.cli --scenario benchmarks/scenarios/short_commands.yaml --providers fake --output benchmarks/results/smoke.json
```

### 12. Model registry and downloads

Implement:

- Voice registry schema validation.
- STT registry validation.
- Download scripts for Silero, Whisper, English Piper voice, Italian Piper voice.
- Checksum verification and attribution checks.
- `make models-min`, `make models-english`, `make models-italian`, `make models-all`, `make models-verify`.

Acceptance checks:

```bash
pytest tests/contract/test_model_manifest.py
python scripts/verify_model_checksums.py --registry model_registry
```

### 13. Containers, CI, and security

Implement or repair:

- CPU, GPU, and dev containers.
- Docker Compose for local backend/web and optional Redis/observability.
- GitHub Actions for backend CI, web client, protocol contract, integration, benchmark smoke, nightly benchmark, model registry, container build, CodeQL, dependency review, license scan, docs, release, and scorecard.
- Release workflow that publishes wheels, source distribution, containers, SBOM, checksums, schemas, and benchmark summary without attaching model files.
- Security docs, threat model, private-data handling, and contributor docs.

Acceptance checks:

```bash
make lint
make test
make smoke
docker compose config
```

## Final definition of done

The repository is ready only when all of these are true:

- `make install` succeeds from a clean checkout.
- `make run` starts the backend and browser demo with development defaults.
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
- Model download/verification commands work and no model binaries are committed.
- CI checks are green with deterministic fake providers.
- README is honest about limitations and does not claim unverified latency guarantees.
- Upstream projects and model sources are attributed.

## Reporting format for the AI coder

At the end of each implementation pass, report:

1. Files changed.
2. Features completed.
3. Tests added or replaced.
4. Exact commands run and whether they passed.
5. Remaining production gaps, if any.
6. Any manual steps needed for real-model demos.

Never hide skipped tests, missing providers, or environment limitations. If a feature is not production-ready, mark it clearly and continue implementing until the definition of done is met.
