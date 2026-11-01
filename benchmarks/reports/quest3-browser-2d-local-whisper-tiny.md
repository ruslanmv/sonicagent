# Quest 3 browser, local Whisper Tiny

One settings microphone test, recorded on the headset. This is not a SonicAgent measurement, not a streaming measurement, and not a percentile. Headset text-to-speech was not measured. Immersive VR and mixed reality were not measured.

| Field | Value |
| --- | --- |
| When | 1 November 2026, 10:17:23 Europe/Rome |
| Run started | 1 November 2026, 10:16:58 Europe/Rome |
| Source | Avatar `settings-mic-test` diagnostic, schema `quest-stt-performance` |
| Surface | Quest Browser, 2D (`browser-2d`) |
| Browser | Oculus Browser 144 / Chromium 144.0.7559.132 |
| Client hint | Quest 3, reported by the browser, not a verified hardware serial |
| CPU / memory | `hardware_concurrency` 3, `device_memory_gb` 8 |
| WASM | SIMD yes, threads 1, `SharedArrayBuffer` no |
| Provider | `local-whisper` |
| Model | `onnx-community/whisper-tiny`, revision `ff4177021cc41f7db950912b73ea4fdf7d01d8e7` |
| Runtime | transformers.js 3.8.1, WASM, dtype `q8`, warm model |
| Language | English |
| Audio | 4139 ms, 48 kHz input, 198656 samples |
| Stop to transcript | 8538 ms |
| Inference | 8348 ms |
| Real-time factor | 2.02 |
| Status | `very_slow` (threshold 3000 ms, critical 8000 ms) |
| Microphone open | 609 ms |
| First audio frame | 50 ms |
| Capture frames | 295, average 28.7 ms, p95 55.6 ms, 33 gaps over 50 ms |
| Transcript | Accepted, 19 characters, 6 output tokens |
| Bottleneck | Inference, described by the diagnostic as dominant |

The model ran slower than the speech. Most of the wait was inside Whisper, and the page skipped frames while it ran. That is the reason to offer a remote speech path. It does not by itself say what the remote path will cost on this headset.

The published SonicAgent HTTP numbers live in `hf-cpu-basic-endpoint-capability.md`. Those numbers are a Linux client calling batch routes. They are not this headset.
