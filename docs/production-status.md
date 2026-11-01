# Production status

SonicAgent serves batch speech today. It is not a production realtime voice assistant, and the Hugging Face Space is not a service level.

## What runs

| Area | State |
| --- | --- |
| Batch speech to text | Multilingual Whisper Tiny on CPU INT8. English, Spanish, French, German, Italian, and Portuguese. |
| Batch speech synthesis | Piper WAV for every voice in `ruslanmv/hp-piper-voices`. Companion and Secretary are the female presets where a female speaker exists. Portuguese voices in that mirror are male and stay labeled male. |
| Voice Studio | Record, then transcribe. Language-scoped voice cards. Card playback. Served at `/` by the voice image and by the Space `ruslanmv/SonicAgent`. |
| Access control | Bearer token on `/v1/audio/*`. The public demo stays off unless `SONIC_PUBLIC_DEMO_ENABLED` is set. |
| Privacy defaults | Audio and transcripts are not stored. Transcript text is not a log field. |
| Hosts | `hf/` image for a local PC, and the same image on the existing Space. CPU Basic can sleep. |
| Measurements | One client-observed HTTP pass is in `benchmarks/reports/hf-cpu-basic-endpoint-capability.md`. |

## Still open

| Area | Why it is still open |
| --- | --- |
| Realtime sessions | The WebSocket accepts a connection. It does not run VAD, transcription, an LLM, or playback. |
| Silero VAD and barge-in | Interfaces only. |
| Streaming LLM | The included provider is a mock. |
| Browser AudioWorklet | The page at `clients/web` is a scaffold. Voice Studio is the browser that runs. |
| Voice checksums | Piper entries in `model_registry/voices.json` still use `TODO` hashes. Whisper Tiny is pinned. |
| OllaBridge and Quest | Cloud does not route audio yet. No physical headset test is claimed. |
| Operations | TLS, short-lived session tokens, origin allowlists, and a reviewed threat model are not finished for a public realtime service. |

## What is safe to do now

- Run the voice image or open Voice Studio on the Space.
- Call the authenticated batch routes.
- Run unit, contract, and web tests.
- Read the endpoint report as a measurement of that client and that host.

## What not to do

- Do not describe the Space as always on, on-device, or a Quest latency result.
- Do not put `SONIC_API_KEY` in a browser build or a public README.
- Do not commit model binaries, private audio, transcripts, local caches, or secrets.
- Do not treat `/health/live` as model readiness.

## Before calling a deployment production

- `make install`, `make test`, and `make lint` pass from a clean checkout.
- Voice checksums replace the `TODO` hashes, and licenses stay attached to the models.
- The security checklist in `docs/security.md` is complete for the exposed routes.
- A new measurement names the machine, the commit, and the warm-up policy, and it is not quoted as a headset service level.
