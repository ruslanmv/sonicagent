# Observability

Observability means knowing what the system is doing without reading private user
content.

## What to measure

The batch API is measured from the client by `make benchmark-endpoints`. A published pass is in `benchmarks/reports/`. That pass does not time the realtime socket.

A finished realtime turn emits `metrics.turn` with `speech_ms`, `stt_ms`, `llm_first_ms`, `tts_first_ms`, and `total_ms`. `/metrics` records `sonicagent_realtime_turns_total`, `sonicagent_realtime_inflight`, and `sonicagent_realtime_stage_seconds` for those three stage fields. Speech start and stop are socket events. Barge-in is a `response.cancelled` result, not a separate cutoff-latency histogram.

For each realtime turn, the socket can report:

- Time until speech starts.
- Time until speech stops.
- Speech-to-text latency.
- Time to first text token.
- Time to first stable phrase.
- Text-to-speech latency.
- Time to first assistant audio.
- Barge-in cancellation time.
- Total turn time.

## Privacy rule

Metrics should not include private audio or transcript content unless the user or
operator explicitly enables storage and logging.

## Metrics endpoint

Prometheus-style metrics are exposed at:

```text
/metrics
```

## Beginner interpretation

If latency feels high, check whether the delay is from speech detection, speech
to text, the text model, text to speech, or browser playback. Each stage needs a
separate metric so operators know where to look.
