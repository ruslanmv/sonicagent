# Production status

SonicAgent serves batch speech and an authenticated realtime turn. The Hugging Face Space is not a service level, and this repository does not claim a Quest result.

## What runs

| Area | State |
| --- | --- |
| Batch speech to text | Multilingual Whisper Tiny on CPU INT8. English, Spanish, French, German, Italian, and Portuguese. |
| Batch speech synthesis | Piper WAV for every voice in `ruslanmv/hp-piper-voices`. Companion and Secretary are the female presets where a female speaker exists. Portuguese voices in that mirror are male and stay labeled male. |
| Voice Studio | Record, then transcribe. Language-scoped voice cards. Card playback. Download speech saves the generated WAV. Served at `/` by the voice image and by the Space `ruslanmv/SonicAgent`. |
| Access control | Bearer token on `/v1/audio/*`. The public demo stays off unless `SONIC_PUBLIC_DEMO_ENABLED` is set. |
| Privacy defaults | Audio and transcripts are not stored. Transcript text is not a log field. |
| Hosts | `hf/` image for a local PC, and the same image on the existing Space. CPU Basic can sleep. |
| Measurements | One client-observed HTTP pass is in `benchmarks/reports/hf-cpu-basic-endpoint-capability.md`. |
| Realtime turn | Bearer-authenticated `POST /v1/sessions`, then one live socket on `/v1/realtime/{id}`. Reconnect after close. Energy endpointing, barge-in, phrase audio when Piper is ready, and OpenAI-compatible or Ollama text when configured. |
| Browser media | `clients/web` resamples, frames PCM, bounds the playback queue, and drops queued audio on `clear_audio`. Voice Studio remains the batch page on the Space. |
| Process metrics | `/metrics` counts realtime turns, inflight turns, and VAD-to-audio stage seconds. Labels do not contain transcript text. |
| Voice checksums | Every `voices.json` entry has a sha256 for the ONNX file and its config. Whisper Tiny stays pinned separately. |

## Still open

| Area | Why it is still open |
| --- | --- |
| Silero file | No Silero file is bundled. Energy endpointing is the detector that runs until the pinned ONNX file is on disk. |
| Default language model | `SONIC_LLM_PROVIDER` defaults to `mock`. Set `ollama` or `openai-compatible` and `SONIC_LLM_BASE_URL` for a real model. |
| OllaBridge and Quest | Cloud does not route audio yet. No physical headset test is claimed. |
| Always-on hosting | TLS in front of your own machine is an operator step. The SBOM script does not sign a release. CPU Basic can sleep. |

## What is safe to do now

- Run the voice image or open Voice Studio on the Space.
- Call the authenticated batch routes.
- Run unit, contract, and web tests.
- Read the endpoint report as a measurement of that client and that host.

## What not to do

- Do not describe the Space as always on, on-device, or a Quest latency result.
- Do not put `SONIC_API_KEY` or a resume token in a browser build, a public README, or an access log.
- Do not commit model binaries, private audio, transcripts, local caches, or secrets.
- Do not treat `/health/live` as model readiness.

## Before calling a deployment production

- `make install`, `make test`, and `make lint` pass from a clean checkout.
- Voice checksums in `voices.json` match the files you install, and licenses stay attached to the models.
- The security checklist in `docs/security.md` is complete for the exposed routes.
- A new measurement names the machine, the commit, and the warm-up policy, and it is not quoted as a headset service level.
