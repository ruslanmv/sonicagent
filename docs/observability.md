# Observability

Observability means knowing what the system is doing without reading private user
content.

## What to measure

The batch API is measured from the client by `make benchmark-endpoints`. A published pass is in `benchmarks/reports/`. The timestamps below belong to the realtime design, which is not running.

For each realtime turn, SonicAgent should measure:

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
