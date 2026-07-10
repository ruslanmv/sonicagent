## Known limitations of the planned v1 design

- faster-whisper does not provide native token-by-token streaming; rolling partial hypotheses are approximate and replaceable.
- Piper synthesis is phrase-pipelined rather than token-level waveform streaming.
- PCM is simple and deterministic but consumes substantially more bandwidth than Opus.
- Browser echo cancellation and microphone processing vary by browser, operating system, and hardware.
- End-to-end latency depends on endpointing settings, selected models, provider location, warm-up state, and compute hardware.
- Model source availability and licenses must be revalidated during release preparation.

