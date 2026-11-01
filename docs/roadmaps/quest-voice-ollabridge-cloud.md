# RFC: SonicAgent voice interoperability with OllaBridge Cloud and 3D-Avatar-Chatbot

**Status:** OllaBridge and Avatar work is still proposed. SonicAgent batch speech, Voice Studio, and the Space `ruslanmv/SonicAgent` are implemented on this branch. This document does not change OllaBridge or the Avatar.  
**Date:** 2026-10-31  
**Target repositories:** [SonicAgent](https://github.com/ruslanmv/sonicagent) (this RFC), [OllaBridge](https://github.com/ruslanmv/ollabridge), [OllaBridge Cloud](https://github.com/ruslanmv/ollabridge-cloud), [3D-Avatar-Chatbot](https://github.com/ruslanmv/3D-Avatar-Chatbot/tree/claude/awesome-brown-khqcdj) (target feature branch)  
**Motivation:** reliable, privacy-aware English/Italian STT and optional TTS for desktop, Meta Quest Browser WebXR VR/MR, and desktop Chrome on Windows through Quest Air Link, with **one OllaBridge pairing** and **no paid Google/Azure/OpenAI speech API dependency**.

> OllaBridge routing, the Avatar provider, and realtime streaming are still proposed. Do not describe those as running. SonicAgent's batch HTTP API is running and is documented in the README.

## 1. Decision and scope

**Decision:** SonicAgent is an independent open-source voice inference service; OllaBridge is the authenticated routing and capability-discovery gateway; OllaBridge Cloud maps a signed-in user to their own connected OllaBridge device and relays bounded requests or future audio sessions; the Avatar remains the only owner of microphone capture, conversation history, avatar animation, and playback.

**Execution preference:** (1) SonicAgent on the user's PC or self-controlled compute, (2) experimentally an eligible HF CPU Space, (3) opt-in in-browser Whisper/Vosk on adequately benchmarked devices. A backend on Hugging Face is still **cloud processing**, even if the hosted model is free. "100% on-device" means inference happens in the Quest/browser with verified local model assets and no network access; it is a distinct mode, not a property of SonicAgent Cloud.

**In scope:** working batch STT, optional batch TTS, health/readiness and model/voice catalogs, origin-scoped authentication, tenant-safe Cloud relay, browser capture adapter, fallback UX, measurement, and incremental real-time streaming.

**Out of scope for the first implementation:** a new LLM/chat engine, replacement of existing Piper TTS in the avatar, changes to 3D renderers, a native Quest APK, proprietary speech APIs, a promise of 100% compatibility, or a production SLA on HF's no-cost tier.

## 2. Verified baseline and gaps

| Repository and source | Verified today | Gap |
| --- | --- | --- |
| SonicAgent [README](../../README.md), [STT module](../../src/sonicagent_rt/stt/faster_whisper.py), [Piper module](../../src/sonicagent_rt/tts/piper_process.py) | Batch Whisper Tiny and batch Piper run. Voice Studio and the Space serve them. | Realtime turns, voice checksum pins, and a production service level |
| SonicAgent [WebSocket endpoint](../../src/sonicagent_rt/api/websocket/endpoint.py) | Accepts a WS, answers ping and cancellation; audio frames are acknowledged as **not implemented** | No VAD, streaming LLM, or barge-in on this socket |
| SonicAgent [session route](../../src/sonicagent_rt/api/routes/sessions.py), [browser capture](../../clients/web/src/audio/capture.ts), [models](../../model_registry/stt_models.json) | Sessions issue a random resume token. Voice Studio is the batch page. Whisper Tiny and Piper file hashes are pinned. | The browser AudioWorklet is still a scaffold |
| OllaBridge [chat route](https://github.com/ruslanmv/ollabridge/blob/master/src/ollabridge/api/main.py), [avatar relay](https://github.com/ruslanmv/ollabridge/blob/master/src/ollabridge/api/avatar_session.py) | Local Ollama-compatible chat and existing authenticated avatar socket relay | No general SonicAgent STT/TTS API |
| OllaBridge local [CloudBridgeManager](https://github.com/ruslanmv/ollabridge/blob/master/src/ollabridge/cloud/bridge_manager.py) | Persistent device-to-cloud relay with reconnect/capability advertisements | No SonicAgent voice capability or dispatch |
| OllaBridge Cloud [RelayHub](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/services/relay_hub.py), [homepilot media pattern](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/api/homepilot_media_bridge.py) | User/device-scoped JSON request-response relay; a media endpoint already converts bounded bytes through base64 | Not a low-latency bidirectional **binary** audio relay; do not send continuous 20ms PCM as JSON RPC |
| OllaBridge Cloud [capability registry](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/services/capability_registry.py) | Structured runtime/model task allowlists | STT and TTS task/runtime kinds are not in current allowlists; design additive migration |
| Avatar [SpeechService](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/js/speech-service.js), [Whisper worker](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/workers/whisper-worker.js) | Browser Web Speech STT, MediaRecorder recording, configurable STT providers; worker pretends to load Whisper | Web Speech may require proprietary remote recognition; WASM worker has no inference; current `/api/stt` fallback has no route |
| Avatar [VRChatIntegration](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/gltf-viewer/VRChatIntegration.js), [CompanionMode](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/CompanionMode.js) | VR controller PTT, separate VR mic UI path and separate hands-free recognizer | Must converge on one provider-agnostic capture/turn controller and one canonical chat history |
| Avatar [TTSProvider](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/TTSProvider.js), [Piper](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/tts/PiperWasmTTSProvider.js) | Existing local/browser TTS and lip-sync pipeline | Preserve as default; remote TTS is optional |

**Correction to earlier proposals:** `MediaRecorder` records/captures audio but does not recognize speech. Availability of `Worker` + `MediaRecorder` does not prove WASM Whisper inference is installed. `SpeechRecognition` may use network services; it must never silently satisfy the "no external STT provider" mode. Native Quest Browser and Chrome over Air Link need **real headset checks**, not an assumed support matrix.

## 3. User journeys and trust boundaries

1. User opens Avatar (HTTPS), has signed in/paired OllaBridge Cloud, selects **Private voice via OllaBridge**.
2. Avatar asks for microphone permission in a user gesture; confirms an active audio track / input level **before** showing "Listening".
3. Avatar records a bounded utterance; it never uploads without active voice consent. Browser/OS/Quest provides the mic, SonicAgent does not bypass permission.
4. Avatar submits to **OllaBridge Cloud user-authenticated voice API**. Cloud resolves a compatible **device owned by this user**; the local OllaBridge dispatches to its private SonicAgent instance (or an explicitly configured eligible remote backend).
5. SonicAgent returns text; Avatar dispatches the exact final text through the existing canonical `handleUserMessage` chat path **once**; existing OllaBridge LLM responds.
6. Avatar speaks via its existing Piper implementation by default; optional SonicAgent Piper output can be used through the same playback/lip-sync abstraction.
7. On permission denial, unavailable backend, device disconnection, sleep, or XR session end: abort/cancel work, close tracks, show a clear status, and retain typed chat.

**Privacy boundary:** HTTPS/WSS is encryption in transit, *not* on-device processing. Cloud relay processes audio bytes transiently if chosen. If all audio must stay on the user's PC/LAN or headset, disable Cloud audio routing and use an explicitly authenticated local/direct transport or an offline in-browser engine.

## 4. API contract v1 — start with batch

These paths are **proposed** and must be exposed **consistently** by both OllaBridge local and OllaBridge Cloud. SonicAgent's internal paths may differ; OllaBridge is the compatibility layer.

### 4.1 Availability and discovery

`GET /v1/audio/capabilities` (requires authenticated identity on Cloud, OllaBridge auth locally):

```json
{
  "version": 1,
  "stt": {"available": true, "ready": true, "mode": "device-relay", "languages": ["en", "es", "fr", "de", "it", "pt"], "models": ["whisper-tiny"], "max_seconds": 15},
  "tts": {"available": true, "ready": true, "voices": ["en_US-lessac-medium", "en_US-kristin-medium", "it_IT-paola-medium", "it_IT-paola-companion"]}
  "realtime": {"available": false, "ready": false, "reason": "not-implemented"},
  "route": {"location": "paired-device", "device_id": "opaque-alias"}
}
```

**Contract semantics:** `available` = compatible route present; `ready` = actual STT/TTS models warmed and callable. Never claim `ready: true` from scaffold route existence. If there is no linked device or the model is cold, report a typed reason. Do not expose other tenants' device IDs or private LAN addresses. No model download during an XR frame/render callback.

### 4.2 Transcription

`POST /v1/audio/transcriptions`: `multipart/form-data` with one audio file, `language=en|es|fr|de|it|pt|auto`, optional `model`, `request_id`; support `audio/webm;codecs=opus` when decodable, or `audio/wav` PCM. Echo cancel and sample-rate negotiation are browser/encoder settings, not server assumptions.

```json
{
  "text": "Can you help me?",
  "language": "en",
  "model": "whisper-base",
  "duration_ms": 1820,
  "request_id": "utt_abc",
  "is_final": true
}
```

`duration_ms` is **measured** audio duration, not a latency promise. Do not synthesize confidence scores when the STT engine does not offer calibrated confidence. Model and content type must reflect what actually ran.

**Phase-1 bounds to validate/tune:** 15 seconds maximum utterance, 2 MiB maximum encoded upload, one active turn per user/device, 30-second processing deadline, bounded concurrency, request cancellation on disconnect, no storage of raw audio/transcripts by default. Always enforce limits at every hop, including **before** base64 decoding.

### 4.3 Speech synthesis

`POST /v1/audio/speech`: JSON `{text, voice, language, format:"wav", request_id}`, constrained text length (e.g. 2,000 characters), output `audio/wav` plus bounded metadata headers, or a versioned JSON response if routing through an existing JSON-only relay.

**Hugging Face voice catalog.** Speech on the Space uses the Piper voices published in [`ruslanmv/hp-piper-voices`](https://huggingface.co/ruslanmv/hp-piper-voices): English (US and UK), Spanish (Spain and Mexico), French, German, Italian, and Portuguese. Each language lists only its own voices. Where a female speaker exists, **Companion** is slower and softer, for an adult companion, and **Secretary** is clearer and slightly faster, for work. Where the mirror has only one female speaker, both profiles share that model and differ by synthesis settings. Spanish (Spain) Companion and Secretary use Sharvard speaker `F` (speaker id 1). Sharvard speaker 0 is offered separately and labeled male. French Companion uses UPMC speaker `jessica` (speaker id 0); Pierre is speaker id 1 and is labeled male. German Companion (Eva K) and Secretary (Kerstin) are lighter, lower-quality models. Portuguese speech is Edresson and Faber, both male and labeled male. The canonical list is [`model_registry/voices.json`](../../model_registry/voices.json).

**Do not replace** the Avatar's working Piper TTS. Optional remote speech must route decoded audio through existing lip-sync/audio-state tracking, with `turn_id` preventing out-of-date playback.

### 4.4 Typed errors

Standardize a stable `code` and descriptive `message` (no secrets): `unauthenticated` (401), `permission_denied` (browser side), `unsupported_codec` (415), `audio_too_large` (413), `invalid_audio` (422), `unsupported_language` (400), `voice_unavailable` (503), `device_offline` (503), `backend_warming` (503 + optional Retry-After), `rate_limited` (429), `timeout` (504), `cancelled` (client event). Distinguish unsupported recognizer from microphone access failure.

## 5. Transport and integration: do not misuse existing Cloud relay

### Stage A: bounded request/response (shipping priority)

```text
Meta Quest / Windows Chrome Browser
  -- HTTPS multipart audio + authenticated account session -->
OllaBridge Cloud /v1/audio/transcriptions
  -- user-owned-device lookup + limits -->
Existing RelayHub JSON request/response
  -- strictly bounded base64 audio with operation sonicagent.stt.transcribe -->
Local OllaBridge CloudBridgeManager on *that user's* PC
  -- localhost HTTP (private token) -->
SonicAgent (faster-whisper) -> final text
  <-- JSON result through same owner-scoped route -->
Avatar -> existing OllaBridge LLM -> existing TTS/lip-sync
```

For a 15-second 16 kHz mono PCM16 utterance, uncompressed audio is about 480 kB before base64 (~640 kB); Opus can be smaller. These are **transport estimates**, not inference latency. Set a hard size ceiling; don't let Cloud's text-frame limits, reverse proxies, or HF hosting consume unbounded RAM. Prefer WebM/Opus batch if decoder and browser support are confirmed; otherwise accept WAV.

Reuse Cloud's [owner-scoped media bridge pattern](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/api/homepilot_media_bridge.py), *without* treating its existing `homepilot.image.*` operations as audio endpoints. Implement new `sonicagent.stt.capability`, `sonicagent.stt.transcribe`, `sonicagent.tts.synthesize` operations, with explicit version and capability flags. Do not change existing chat, image, or avatar operations.

**Alternative:** If the deployment has a secured direct HTTPS SonicAgent endpoint, OllaBridge can proxy to it directly, avoiding base64 relay overhead. The user's HTTPS Vercel page must not call a plain HTTP or WS private LAN endpoint and assume that works in Quest Browser; design for proper TLS, authentication, browser private-network constraints, and not publishing unprotected local ports.

### Stage B: genuinely real-time voice (separate later PR)

`POST /v1/audio/sessions` -> scoped, short-lived, single-use session token; `WSS /v1/audio/realtime/{session_id}` -> multiplexed binary PCM16 frames plus typed JSON events. The existing [SonicAgent 24-byte frame v1](../api/binary-frame.md) is the **backend audio protocol**, *not* automatically supported by Cloud's existing JSON RelayHub.

Build a **new owner-scoped streaming relay** or an explicitly secured direct WSS path that can forward binary frames without JSON/base64 amplification at 20 ms cadence. Implement bounded per-session input/output queues, frame sizes, backpressure, sequence checks, cancellable turns, heartbeats, expiry, browser `AudioWorklet` capture/playback, audio clock tracking, and half-open recovery. Reuse existing device pairing but **do not** share global pending-request maps across tenants or trust client-supplied device IDs.

Keep source STT and LLM separate: `transcript.final` goes to Avatar's canonical conversation once unless the user explicitly chooses a server-orchestrated voice call, in which case define who owns the LLM/TTS and suppress duplicate requests.

## 6. SonicAgent implementation tasks

### P0 — batch STT

Done in SonicAgent. `POST /v1/audio/transcriptions` runs multilingual Tiny on CPU INT8 for English, Spanish, French, German, Italian, and Portuguese. `/health/ready` waits for the loaded model. The Tiny checkpoint is pinned. A physical Quest microphone has not been tested.

### P1 — batch Piper

Done in SonicAgent. `POST /v1/audio/speech` returns a WAV for the `hp-piper-voices` mirror, including Companion and Secretary presets. Voice file hashes are pinned. The realtime socket speaks phrases when Piper is ready. OllaBridge does not route that audio yet.

### P2 — realtime session services
- Implement `sessions/manager.py`, `auth/*`, `api/websocket/endpoint.py`, `audio/*`, VAD, endpointing, STT turns, cancellation/turn IDs, a **single** LLM owner, TTS queueing, barge-in/echo guard, and proper cleanup.
- Implement browser `clients/web/src/audio/capture.ts` AudioWorklet with explicit sample-rate conversion, mute policy, XR visibility lifecycle, device change/track-ended events, network backpressure; verify Python/TS binary protocol parity.
- Never use `SpeechRecognition` as a privacy-preserving default. It is opt-in only when cloud speech recognition is permitted and its provider behavior is understood.

### P3 — deployment

Done for the speech image. `hf/` builds the CPU image, and the existing Space `ruslanmv/SonicAgent` runs it. CPU Basic can sleep. It is not an always-on production host. A Compose profile that places SonicAgent on a private network next to OllaBridge is still open.

## 7. Cross-repository implementation order (split PRs)

| Order | Repository | Suggested changes | Merge gate |
| --- | --- | --- | --- |
| RFC (this PR) | **SonicAgent** | This spec, endpoints, security architecture, QA checklist | Review contracts and trust boundaries |
| 1 | **SonicAgent** | Batch faster-whisper, tests, readiness, pinned models, container. **Done on this branch.** | English and Italian fixtures pass on CPU; negative tests; no fake results |
| 2 | **OllaBridge (local)** | New voice service config/health + CloudBridgeManager `sonicagent.*` dispatch and capability ads | Existing chat/avatar relay tests unchanged; backend not ready -> explicit unavailability |
| 3 | **OllaBridge Cloud** | Owner-scoped voice proxy and token checks; bounded base64 RPC on existing JSON relay | Cross-tenant requests denied; disconnected device behavior deterministic; authenticated request works |
| 4 | **3D-Avatar-Chatbot** | New `ollabridge-voice` provider, MediaRecorder PTT, transcript integration, diagnostics, feature flag | Quest + Air Link capture and final transcript; exactly one chat turn |
| 5 | **SonicAgent** | Piper WAV synthesis and the voice registry. **Done for batch WAV.** Realtime cancellation remains open. | Playable audio for the mirror; existing avatar TTS still works |
| 6 | **OllaBridge local/Cloud + SonicAgent + Avatar** | Streaming WSS relay, AudioWorklet, VAD, barge-in, speaking states | End-to-end streamed headset test; no cross-tenant leakage; no VR frame regression |
| 7 | **Deployment** | The Space `ruslanmv/SonicAgent` is deployed. Dashboards and a headset comparison remain open. | Cold start and sleep stay documented; the Space is not the required primary path |

## 8. Avatar integration details (important)

- Add a provider-agnostic `startSTT` / `stopSTT` or equivalent transcript event source in [`js/speech-service.js`](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/js/speech-service.js). Do **not** fork or shadow its `handleUserMessage` pipeline.
- Use the same controller in VR PTT [`VRChatIntegration.js`](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/gltf-viewer/VRChatIntegration.js), the settings mic, AR overlay, and hands-free [`CompanionMode.js`](https://github.com/ruslanmv/3D-Avatar-Chatbot/blob/claude/awesome-brown-khqcdj/src/CompanionMode.js). Existing CompanionMode has its own `SpeechRecognition`; simply adding a provider to SpeechService **will not enable hands-free Quest**. Centralize or adapt without two mic owners.
- Fix async press/release race: when VR button is released while permission or `getUserMedia` is pending, do not start late recording. Serialize/cancel starts by generation token.
- Handle `MediaStreamTrack.onended`, `devicechange`, `NotAllowedError`, `NotFoundError`, `NotReadableError`, `AbortError`, `XRSession.visibilityState`, session end, network loss. Confirm mic input is live with track state and measured audio level, not merely a resolved permission.
- Use browser-supported constraints as preferences: `echoCancellation`, `noiseSuppression`, `autoGainControl`; examine `track.getSettings()`; do not assume exact Quest mic device names, 48kHz guaranteed, or browser ASR presence.
- Route final transcript to existing chat **once**; interim results can be displayed but not dispatched as final turns. Add request and turn IDs to deduplicate retries.
- Preserve `TTSProvider`, `PiperWasmTTSProvider`, visemes/lip-sync, persona, chat history, VR controllers, and AR placement. Make remote TTS a separate opt-in provider.
- Add a clear on-screen mode: **Offline in-browser (experimental)** / **OllaBridge self-hosted** / **OllaBridge Cloud relay (audio leaves device)** / **Text only**. Privacy-preserving mode must not silently fall back to Chrome/Web Speech's possible network service.
- The Avatar's `workers/whisper-worker.js` currently contains a **placeholder**. Only advertise offline ASR after replacing it with a real pinned model runtime and benchmarking on physical Quest; verify cache/WASM/WebGPU and no background network calls after assets are provisioned.

## 9. Hugging Face feasibility gate — verify before promising free API hosting

Current official HF documentation: [Spaces Overview](https://huggingface.co/docs/hub/spaces-overview), [Manage Spaces](https://huggingface.co/docs/huggingface_hub/main/en/guides/manage-spaces).

As of this RFC, **CPU Basic** advertises **2 vCPU / 16 GB RAM / $0 hourly compute**, **but creating new compute-backed Docker/Gradio Spaces on CPU Basic requires an eligible subscription**; Static Spaces are free to everyone. Existing grants/Spaces/account eligibility must be checked explicitly. Free compute may sleep and has nonpersistent storage. No guarantee of always-on voice sessions, realtime QoS, free GPU, unlimited concurrent inference, or free-account Docker creation. Do not build a mandatory dependency on this tier.

The existing Space `ruslanmv/SonicAgent` serves this FastAPI image on CPU Basic, with Whisper Tiny pinned and the Piper mirror installed at build time. It can sleep, cold-start, and run out of memory. The HF token and `SONIC_API_KEY` stay server-side. One HTTP measurement is published in `benchmarks/reports/hf-cpu-basic-endpoint-capability.md`. That pass is not a word-error-rate study and not a Quest result. OllaBridge Cloud is a separate hop and is not routing audio yet. If that relay is also a Space, test both hops before promising a headset path.

## 10. Compatibility and QA matrix

| Scenario | Capture source | STT route | Required test |
| --- | --- | --- | --- |
| Desktop Chrome (non-VR) | Selected OS mic | Local/Cloud OllaBridge | Permission grant/deny, playback, device switch |
| Quest 3 native Browser 2D | Quest mic through `getUserMedia` | Cloud relay to PC SonicAgent | Actual recording, valid English/Italian transcript, TTS |
| Quest 3 native Browser WebXR VR | Same browser mic | Cloud relay to PC | Controller PTT timing, XR entry/exit, 30-turn stability |
| Quest 3 native Browser WebXR MR/AR | Browser mic where supported | Cloud relay to PC | AR placement, conversation, headset visibility changes |
| Quest 3 with Air Link + Windows Chrome WebXR | Windows input exposed by Meta Link, **not guaranteed** | Cloud relay/local PC | Windows mic routing, actual audio levels, WebXR session/frame health |
| Browser offline / Quest without network | Mic only | Optional pinned browser-local ASR | Explicit mode, no external fetches, VR FPS and memory benchmark |
| Backend sleep/offline/disconnect | Any | None | No spinning mic/false "listening"; typed chat remains |
| Compromised or wrong account/device | Any | Reject | Tenant isolation and revoked credentials |
| Busy/noisy room, feedback during TTS | Any | Local/Cloud | AEC, false barge-in, endpointing and echo tests |

**Test layers:**
- Unit: decoder, permission errors, locale, strict schemas, audio size limits, transcript dedupe, audio state machine, TTS cancellation.
- Contract: JSON REST, model manifests, Python/TypeScript 24-byte binary parity, Cloud-to-device operation names, version mismatch.
- Integration: SonicAgent with real models on CPU and fake upstream LLM, Ollabridge local + Cloud paired owner device; deliberate backend sleep/offline/reconnect; competing requests.
- Security: no cross-tenant routing; public unauthenticated calls rejected; no dev JWT or `X-User-Id` shortcut in production; rate/quotas; token expiry; CORS/origin, CSRF where cookies apply; redacted logs; fuzz malformed WebM/WAV/frame headers.
- Browser/XR: Playwright simulated media streams and WebXR emulator for deterministic app logic, **not** as substitutes for physical Meta Quest testing.
- Physical: Quest Browser VR/MR, Quest 3 Air Link Windows Chrome, audio devices and mute/unmute, varying Wi-Fi, headset sleep, mic switch, 30-turn conversation, entering/leaving immersive session.

**Metrics / release gates (define baselines before choosing thresholds):** STT word error rate on a versioned English+Italian dataset; p50/p95 time from end-of-speech to final transcript split by local vs Cloud vs HF, cold vs warm; mic acquisition success; first synthesized audio; percent of failed/silent recordings; XR frame timing and FPS regression vs no-ASR build; dropped frames, cancellation-to-silence, backend CPU/RAM, 2-hour soak and resource cleanup. Reject fabricated sub-second latency claims. Target zero duplicate canonical chat turns, zero unconsented upload, zero cross-tenant audio leakage and zero silent paid-service fallback.

## 11. Failure and rollback behavior

- `SONIC_VOICE_ENABLED=false` on SonicAgent or `OLLABRIDGE_VOICE_ENABLED=false` (proposed switch; name subject to final conventions) at gateway layer disables new APIs without affecting chat.
- Cloud voice routes only advertised when linked device explicitly declares `sonicagent.stt` / `sonicagent.tts` and real backend readiness succeeds. Older OllaBridge versions remain supported for text/chat.
- On error, clean tracks, audio contexts, sockets, recordings, timers and queued speech; surface status + text input. Never automatically downgrade private STT to proprietary browser recognition.
- Preserve API v1 compatibility and backwards-compatible capability additions; all new routes additive. Deployment must support rollback independently per repository.
- Release gradually: off -> internal developer setting -> headset beta -> opt-in public feature -> stable after real-device metrics.

## 12. Acceptance criteria / definition of done

SonicAgent batch transcription from the WAV fixtures, `/health/ready`, batch Piper WAVs, and the conditional Space deployment are in place. The boxes below stay open because each one still includes OllaBridge, the Avatar, or a physical headset.

- [ ] Real faster-whisper inference returns a correct **non-placeholder** transcript from deterministic WAV and WebM fixtures and from a real Quest microphone.
- [ ] `/health/ready` and capability discovery accurately report warm vs unsupported/unavailable engine; no fake success.
- [ ] A Cloud account can reach **only its own paired** SonicAgent via a bounded, authenticated request; revoked/offline devices fail safely.
- [ ] No Google/Azure/OpenAI paid speech API calls or hidden cloud-recognizer fallback in "private speech" mode.
- [ ] VR controller PTT, settings mic, AR mic, and hands-free calls share a single capture owner and call the canonical chat path once.
- [ ] Existing Avatar chat/animation/lip-sync, local Piper, and OllaBridge model/chat routing pass regressions without enabled voice service.
- [ ] Optional Piper backend delivers playable, cancellable audio and does not double-play with local TTS.
- [ ] Real-time WSS transport is binary, owner-scoped, bounded, and isolated from the existing JSON request relay; tested for barge-in and reconnect.
- [ ] Quest Browser and Air Link paths pass **physical** validation; no assertion of universal or "100%" compatibility without platform/version coverage.
- [ ] HF deployment is documented **as conditional and best-effort**; no default reliance on a free HF compute Space.
- [ ] Licenses and model cards are reviewed: SonicAgent currently declares GPL-3.0-or-later; Avatar Apache-2.0. Keep services separate and assess distribution obligations before copying runtime code.

## 13. Implementation references

- SonicAgent backend code: [FastAPI factory](../../src/sonicagent_rt/api/app_factory.py), [config](../../src/sonicagent_rt/config.py), [binary protocol](../../src/sonicagent_rt/protocol/binary_frame.py), [contracts](../api/websocket-events.md), [model registry](../../model_registry/).
- Cross-repo auth/tenant boundaries: [Cloud relay](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/api/relay.py), [RelayHub](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/services/relay_hub.py), [owner-scoped media](https://github.com/ruslanmv/ollabridge-cloud/blob/master/src/ollabridge_cloud/api/homepilot_media_bridge.py), [local Cloud bridge](https://github.com/ruslanmv/ollabridge/blob/master/src/ollabridge/cloud/bridge_manager.py).
- Core browser API background: [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [MediaRecorder](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder), [AudioWorklet](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet).
- Alternative browser-local engine: [Transformers.js](https://huggingface.co/docs/transformers.js/index). Only label a model **offline** after preloading/pinning its binary assets and verifying zero network access during inference.

**Next action:** implement the OllaBridge owner-scoped voice relay. Do not begin streaming until that binary relay design is independently reviewed. SonicAgent batch speech is no longer the next task.
