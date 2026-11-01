# Benchmarks

`benchmarks/cli.py` is still the deterministic scaffold used by `make benchmark-smoke`. Its latency fields are placeholders.

`benchmarks/endpoints/` measures the live HTTP speech API: health, a preset WAV download, speech synthesis, and transcription. The client records time to the first response byte and time to the complete body. Batch speech has no partial audio, so those two moments are the wait before a headset could start playback.

```bash
export SONIC_API_KEY=your-service-token
python -m benchmarks.endpoints.probe \
  --base-url https://ruslanmv-sonicagent.hf.space \
  --repeats 5 \
  --output benchmarks/results/endpoints.json \
  --markdown benchmarks/reports/endpoint-capability.md
```

Without `SONIC_API_KEY`, the probe uses the public demo and keeps the sample count small. Results under `benchmarks/results/` stay out of Git. A published snapshot belongs in `benchmarks/reports/` only after a real run.

The published HTTP numbers describe one Linux client and one host. They are not a Quest, phone, or glasses measurement, and they are not a service level.

`benchmarks/reports/quest3-browser-2d-local-whisper-tiny.md` is a separate, single headset run of local Whisper Tiny in the Quest 3 browser. It is not a SonicAgent streaming result.
