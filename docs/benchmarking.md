## Latency and benchmark policy

SonicAgent is designed for measurable low-latency operation. Every report must document:

- Commit hash and dirty state.
- Date and operating system.
- CPU, RAM, GPU, driver, and power mode.
- VAD, STT, LLM, and TTS providers and model identifiers.
- Session count, utterance set, warm-up policy, and network conditions.
- P50, P95, P99, sample count, errors, and cancellations.

Required turn timestamps include speech start/stop, STT start/final, LLM request/first token, first phrase, TTS start, first audio, completion, barge-in detection, and audio cancellation.

Run the deterministic scaffold benchmark:

```bash
make benchmark-smoke
```

That scaffold does not call Whisper or Piper. Measure the running HTTP API with:

```bash
export SONIC_API_KEY=your-service-token
make benchmark-endpoints
```

The command writes `benchmarks/results/endpoints.json`. Read [`benchmarks/README.md`](../benchmarks/README.md) before quoting a figure. A headset still waits for the full WAV, because realtime playback is not implemented.

