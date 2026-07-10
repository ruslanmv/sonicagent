## Production implementation sequence

Complete the system in this order so that transport contracts remain stable while inference providers are added:

1. **Protocol and sessions** — finalize JSON events, binary header, authentication, reconnect, sequence validation, queue limits, and golden fixtures.
2. **Browser media** — complete AudioWorklet capture/playback, resampling, echo handling, playback timestamps, and backpressure.
3. **VAD and endpointing** — integrate Silero ONNX, pre-roll, speech start/stop events, and noisy-room tests.
4. **STT** — integrate faster-whisper worker pools, final transcripts, language handling, and optional rolling partial hypotheses.
5. **LLM streaming** — implement OpenAI-compatible and Ollama clients with deadlines, retries, cancellation, and redacted telemetry.
6. **Phrase-pipelined TTS** — integrate Piper, model cache, worker processes, phrase scheduling, PCM framing, and cancellation.
7. **Barge-in** — cancel the active turn, purge all unsent audio, notify the client, and validate cutoff latency.
8. **Observability and benchmarks** — measure VAD, endpointing, STT, LLM TTFT, TTS, first audio, cancellation, and concurrency.
9. **Security and operations** — threat model, rate limiting, session isolation, secret handling, SBOM, signing, runbooks, and load testing.

