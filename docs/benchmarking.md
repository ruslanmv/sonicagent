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

Real-model benchmark commands remain disabled until providers are implemented and model hashes are pinned.

