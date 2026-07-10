# Complete project tree

Generated from this scaffold.

```text
SonicAgent/
├── .devcontainer/
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── post-create.sh
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── benchmark_report.yml
│   │   ├── bug_report.yml
│   │   ├── config.yml
│   │   ├── documentation.yml
│   │   ├── feature_request.yml
│   │   └── voice_model_request.yml
│   ├── workflows/
│   │   ├── benchmark-nightly.yml
│   │   ├── benchmark-smoke.yml
│   │   ├── ci.yml
│   │   ├── codeql.yml
│   │   ├── container-build.yml
│   │   ├── dependency-review.yml
│   │   ├── docs.yml
│   │   ├── integration.yml
│   │   ├── license-scan.yml
│   │   ├── model-registry-check.yml
│   │   ├── protocol-contract.yml
│   │   ├── release.yml
│   │   ├── scorecard.yml
│   │   └── web-client.yml
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── release-drafter.yml
├── .vscode/
│   ├── extensions.json
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── assets/
│   ├── branding/
│   │   ├── favicon.svg
│   │   ├── logo-dark.svg
│   │   ├── logo.svg
│   │   └── social-preview.png
│   ├── demo/
│   │   ├── architecture-preview.png
│   │   ├── browser-call-screen.png
│   │   ├── latency-dashboard.png
│   │   └── sonicagent-demo.gif
│   └── diagrams/
│       ├── audio-frame-layout.svg
│       ├── barge-in-sequence.svg
│       ├── deployment-topology.svg
│       ├── system-architecture.svg
│       └── turn-sequence.svg
├── benchmarks/
│   ├── datasets/
│   │   ├── manifest.schema.json
│   │   ├── README.md
│   │   └── sample_manifest.json
│   ├── hardware/
│   │   ├── example_cpu.yaml
│   │   ├── example_gpu.yaml
│   │   └── schema.json
│   ├── reports/
│   │   ├── README.md
│   │   ├── report-template.md
│   │   └── sample-report.md
│   ├── results/
│   │   └── .gitkeep
│   ├── scenarios/
│   │   ├── barge_in.yaml
│   │   ├── cpu_english.yaml
│   │   ├── cpu_italian.yaml
│   │   ├── gpu_english.yaml
│   │   ├── long_response.yaml
│   │   ├── noisy_room.yaml
│   │   └── short_commands.yaml
│   ├── stages/
│   │   ├── benchmark_audio_ingress.py
│   │   ├── benchmark_barge_in.py
│   │   ├── benchmark_concurrency.py
│   │   ├── benchmark_first_audio.py
│   │   ├── benchmark_llm_ttft.py
│   │   ├── benchmark_stt.py
│   │   ├── benchmark_tts.py
│   │   └── benchmark_vad.py
│   ├── __init__.py
│   ├── cli.py
│   ├── README.md
│   ├── report.py
│   ├── runner.py
│   └── statistics.py
├── clients/
│   ├── python/
│   │   ├── examples/
│   │   │   ├── save_assistant_audio.py
│   │   │   ├── stream_microphone.py
│   │   │   └── stream_wav_file.py
│   │   ├── src/
│   │   │   └── sonicagent_client/
│   │   │       ├── __init__.py
│   │   │       ├── audio.py
│   │   │       ├── client.py
│   │   │       ├── events.py
│   │   │       ├── exceptions.py
│   │   │       ├── protocol.py
│   │   │       └── session.py
│   │   ├── tests/
│   │   │   ├── test_client.py
│   │   │   └── test_protocol.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── web/
│   │   ├── public/
│   │   │   ├── favicon.svg
│   │   │   └── manifest.webmanifest
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── modelsApi.ts
│   │   │   │   └── sessionApi.ts
│   │   │   ├── audio/
│   │   │   │   ├── worklets/
│   │   │   │   │   ├── capture.processor.ts
│   │   │   │   │   └── playback.processor.ts
│   │   │   │   ├── audioQueue.ts
│   │   │   │   ├── capture.ts
│   │   │   │   ├── levelMeter.ts
│   │   │   │   ├── playback.ts
│   │   │   │   └── resampler.ts
│   │   │   ├── protocol/
│   │   │   │   ├── binaryFrame.ts
│   │   │   │   ├── constants.ts
│   │   │   │   ├── controlEvents.ts
│   │   │   │   └── validation.ts
│   │   │   ├── realtime/
│   │   │   │   ├── latencyTracker.ts
│   │   │   │   ├── realtimeClient.ts
│   │   │   │   ├── reconnect.ts
│   │   │   │   └── turnManager.ts
│   │   │   ├── state/
│   │   │   │   ├── callState.ts
│   │   │   │   └── settingsStore.ts
│   │   │   ├── ui/
│   │   │   │   ├── CallPanel.ts
│   │   │   │   ├── LatencyPanel.ts
│   │   │   │   ├── SettingsPanel.ts
│   │   │   │   ├── TranscriptPanel.ts
│   │   │   │   ├── VoiceSelector.ts
│   │   │   │   └── Waveform.ts
│   │   │   ├── app.ts
│   │   │   ├── main.ts
│   │   │   └── styles.css
│   │   ├── tests/
│   │   │   ├── audioQueue.test.ts
│   │   │   ├── binaryFrame.test.ts
│   │   │   ├── latencyTracker.test.ts
│   │   │   └── turnManager.test.ts
│   │   ├── eslint.config.js
│   │   ├── index.html
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   ├── README.md
│   │   ├── tsconfig.json
│   │   └── vite.config.ts
│   └── README.md
├── configs/
│   ├── profiles/
│   │   ├── benchmark.yaml
│   │   ├── cpu-balanced.yaml
│   │   ├── cpu-low-latency.yaml
│   │   ├── english-demo.yaml
│   │   ├── gpu-low-latency.yaml
│   │   └── italian-demo.yaml
│   ├── base.yaml
│   ├── development.yaml
│   ├── logging.yaml
│   ├── README.md
│   └── testing.yaml
├── deploy/
│   ├── compose/
│   │   ├── docker-compose.gpu.yml
│   │   ├── docker-compose.observability.yml
│   │   ├── docker-compose.redis.yml
│   │   └── docker-compose.yml
│   ├── docker/
│   │   ├── Dockerfile.cpu
│   │   ├── Dockerfile.dev
│   │   ├── Dockerfile.gpu
│   │   ├── entrypoint.sh
│   │   └── healthcheck.py
│   ├── observability/
│   │   ├── grafana/
│   │   │   ├── dashboards/
│   │   │   │   └── sonicagent-latency.json
│   │   │   └── datasources.yaml
│   │   ├── otel-collector.yaml
│   │   └── prometheus.yml
│   ├── proxy/
│   │   ├── nginx.conf
│   │   └── README.md
│   └── README.md
├── docs/
│   ├── adr/
│   │   ├── 0001-websocket-control-and-binary-audio.md
│   │   ├── 0002-server-side-vad.md
│   │   ├── 0003-faster-whisper-backend.md
│   │   ├── 0004-phrase-pipelined-piper.md
│   │   ├── 0005-provider-interfaces.md
│   │   ├── 0006-models-not-stored-in-git.md
│   │   ├── 0007-licensing-strategy.md
│   │   └── README.md
│   ├── api/
│   │   ├── binary-frame.md
│   │   ├── errors.md
│   │   ├── rest-api.md
│   │   └── websocket-events.md
│   ├── diagrams/
│   │   ├── architecture.mmd
│   │   ├── barge-in-sequence.mmd
│   │   ├── deployment.mmd
│   │   └── turn-sequence.mmd
│   ├── runbooks/
│   │   ├── audio-dropouts.md
│   │   ├── gpu-out-of-memory.md
│   │   ├── high-latency.md
│   │   ├── model-download-failure.md
│   │   └── websocket-disconnections.md
│   ├── architecture.md
│   ├── audio-format.md
│   ├── authentication.md
│   ├── barge-in.md
│   ├── benchmarking.md
│   ├── configuration.md
│   ├── deployment.md
│   ├── getting-started.md
│   ├── index.md
│   ├── latency-budget.md
│   ├── licensing.md
│   ├── limitations.md
│   ├── model-registry.md
│   ├── observability.md
│   ├── phrase-pipelining.md
│   ├── privacy.md
│   ├── protocol.md
│   ├── roadmap.md
│   ├── security.md
│   ├── speech-recognition.md
│   ├── speech-synthesis.md
│   ├── text-generation.md
│   ├── troubleshooting.md
│   └── vad.md
├── examples/
│   ├── italian_voice/
│   │   └── config.yaml
│   ├── minimal_browser/
│   │   ├── client.js
│   │   └── index.html
│   ├── ollama/
│   │   └── config.yaml
│   ├── openai_compatible_llm/
│   │   └── config.yaml
│   ├── python_microphone/
│   │   └── main.py
│   ├── python_wav/
│   │   └── main.py
│   └── README.md
├── model_registry/
│   ├── checksums/
│   │   ├── stt-models.sha256
│   │   └── voices.sha256
│   ├── schemas/
│   │   ├── model-bundle.schema.json
│   │   ├── stt-model.schema.json
│   │   └── voice.schema.json
│   ├── default-models.json
│   ├── README.md
│   ├── stt_models.json
│   └── voices.json
├── scripts/
│   ├── benchmark.sh
│   ├── bootstrap.sh
│   ├── dev.sh
│   ├── download_default_models.py
│   ├── download_stt_model.py
│   ├── download_voice.py
│   ├── export_openapi.py
│   ├── export_protocol_schema.py
│   ├── format.sh
│   ├── generate_architecture_diagrams.py
│   ├── generate_test_audio.py
│   ├── lint.sh
│   ├── release_check.py
│   ├── smoke.sh
│   ├── sync_voice_registry.py
│   ├── test.sh
│   ├── validate_licenses.py
│   └── verify_model_checksums.py
├── src/
│   └── sonicagent_rt/
│       ├── api/
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── health.py
│       │   │   ├── metrics.py
│       │   │   ├── models.py
│       │   │   ├── readiness.py
│       │   │   ├── sessions.py
│       │   │   └── voices.py
│       │   ├── websocket/
│       │   │   ├── __init__.py
│       │   │   ├── disconnect.py
│       │   │   ├── endpoint.py
│       │   │   ├── handshake.py
│       │   │   ├── receiver.py
│       │   │   └── sender.py
│       │   ├── __init__.py
│       │   ├── app_factory.py
│       │   ├── dependencies.py
│       │   ├── errors.py
│       │   └── middleware.py
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── backpressure.py
│       │   ├── chunker.py
│       │   ├── formats.py
│       │   ├── frame.py
│       │   ├── jitter_buffer.py
│       │   ├── normalizer.py
│       │   ├── outbound_queue.py
│       │   ├── pcm.py
│       │   ├── resampler.py
│       │   ├── ring_buffer.py
│       │   └── wav.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── jwt.py
│       │   ├── models.py
│       │   ├── permissions.py
│       │   ├── session_tokens.py
│       │   └── websocket_auth.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── factory.py
│       │   ├── mock.py
│       │   ├── models.py
│       │   ├── ollama.py
│       │   ├── openai_compatible.py
│       │   ├── prompts.py
│       │   └── token_stream.py
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── latency_metrics.py
│       │   ├── metrics.py
│       │   ├── redaction.py
│       │   ├── session_metrics.py
│       │   ├── structured_logging.py
│       │   └── tracing.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── barge_in.py
│       │   ├── cancellation.py
│       │   ├── error_recovery.py
│       │   ├── latency.py
│       │   ├── orchestrator.py
│       │   ├── phrase_pipeline.py
│       │   ├── tasks.py
│       │   ├── turn.py
│       │   └── turn_state.py
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── binary_frame.py
│       │   ├── codecs.py
│       │   ├── constants.py
│       │   ├── control_events.py
│       │   ├── envelope.py
│       │   ├── errors.py
│       │   ├── sequence.py
│       │   ├── server_events.py
│       │   └── validation.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── input_validation.py
│       │   ├── log_redaction.py
│       │   ├── origin_policy.py
│       │   ├── payload_limits.py
│       │   ├── privacy.py
│       │   └── rate_limits.py
│       ├── sessions/
│       │   ├── __init__.py
│       │   ├── cleanup.py
│       │   ├── lifecycle.py
│       │   ├── limits.py
│       │   ├── manager.py
│       │   ├── memory_store.py
│       │   ├── models.py
│       │   ├── redis_store.py
│       │   └── state.py
│       ├── stt/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── factory.py
│       │   ├── faster_whisper.py
│       │   ├── language_detection.py
│       │   ├── models.py
│       │   ├── partial_stabilizer.py
│       │   ├── rolling_window.py
│       │   ├── utterance_buffer.py
│       │   └── worker_pool.py
│       ├── tts/
│       │   ├── __init__.py
│       │   ├── audio_framer.py
│       │   ├── base.py
│       │   ├── factory.py
│       │   ├── model_cache.py
│       │   ├── models.py
│       │   ├── phrase_segmenter.py
│       │   ├── piper_external.py
│       │   ├── piper_process.py
│       │   ├── synthesis_cache.py
│       │   ├── text_normalizer.py
│       │   ├── voice_registry.py
│       │   └── worker_pool.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── async_tools.py
│       │   ├── clocks.py
│       │   ├── ids.py
│       │   ├── json.py
│       │   └── shutdown.py
│       ├── vad/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── endpointing.py
│       │   ├── energy_fallback.py
│       │   ├── events.py
│       │   ├── factory.py
│       │   └── silero_onnx.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── cli.py
│       ├── config.py
│       ├── constants.py
│       ├── lifespan.py
│       └── version.py
├── tests/
│   ├── contract/
│   │   ├── test_binary_protocol.py
│   │   ├── test_model_manifest.py
│   │   ├── test_python_ts_protocol_parity.py
│   │   ├── test_rest_schema.py
│   │   └── test_websocket_events.py
│   ├── e2e/
│   │   ├── test_audio_output_file.py
│   │   ├── test_browser_smoke.py
│   │   ├── test_english_conversation.py
│   │   └── test_italian_conversation.py
│   ├── fakes/
│   │   ├── fake_clock.py
│   │   ├── fake_llm.py
│   │   ├── fake_stt.py
│   │   ├── fake_tts.py
│   │   └── fake_vad.py
│   ├── fixtures/
│   │   ├── audio/
│   │   │   ├── generated_speech_manifest.json
│   │   │   ├── README.md
│   │   │   ├── silence_1s.wav
│   │   │   └── tone_440hz.wav
│   │   ├── events/
│   │   │   ├── response_cancel.json
│   │   │   ├── session_update.json
│   │   │   └── transcript_final.json
│   │   └── models/
│   │       └── test_voice_registry.json
│   ├── golden/
│   │   ├── protocol/
│   │   │   ├── binary-frame-v1.hex
│   │   │   └── event-sequence-v1.json
│   │   └── reports/
│   │       └── latency-report.json
│   ├── integration/
│   │   ├── test_audio_ingress.py
│   │   ├── test_barge_in_cancellation.py
│   │   ├── test_full_turn.py
│   │   ├── test_llm_stream.py
│   │   ├── test_model_cache.py
│   │   ├── test_piper_synthesis.py
│   │   ├── test_reconnect.py
│   │   ├── test_session_lifecycle.py
│   │   ├── test_stt_pipeline.py
│   │   ├── test_vad_endpointing.py
│   │   └── test_websocket_auth.py
│   ├── performance/
│   │   ├── test_barge_in_deadline.py
│   │   ├── test_concurrent_sessions.py
│   │   ├── test_frame_throughput.py
│   │   └── test_queue_memory_bound.py
│   ├── unit/
│   │   ├── test_backpressure.py
│   │   ├── test_barge_in.py
│   │   ├── test_binary_frame.py
│   │   ├── test_cancellation.py
│   │   ├── test_config.py
│   │   ├── test_control_events.py
│   │   ├── test_endpointing.py
│   │   ├── test_jitter_buffer.py
│   │   ├── test_latency_metrics.py
│   │   ├── test_partial_stabilizer.py
│   │   ├── test_phrase_segmenter.py
│   │   ├── test_resampler.py
│   │   ├── test_ring_buffer.py
│   │   ├── test_sequence.py
│   │   ├── test_session_state.py
│   │   └── test_voice_registry.py
│   ├── conftest.py
│   └── README.md
├── tools/
│   ├── protocol_codegen.py
│   ├── README.md
│   ├── registry_validator.py
│   └── release_notes.py
├── .dockerignore
├── .editorconfig
├── .env.example
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── CHANGELOG.md
├── CITATION.cff
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── docker-compose.yml
├── GOVERNANCE.md
├── LICENSE
├── Makefile
├── mkdocs.yml
├── pyproject.toml
├── README.md
├── SCAFFOLD_MANIFEST.json
├── SECURITY.md
├── SUPPORT.md
├── THIRD_PARTY_NOTICES.md
├── uv.lock
└── VERSION
```
