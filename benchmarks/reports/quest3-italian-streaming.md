# Italian streaming on the Quest client path — desktop and server measurements

2026-11-22. PR #86 (Aurora Medium, Giorgio High) against Paola Medium and Serena
High. **Desktop Chromium and a local server, not a headset**: see "Still needs a
Quest 3" at the end.

## Path measured

The 3D Avatar Chatbot's own TTS modules, unmodified, in headless Chromium 157
(`RemoteSonicAgentTTS.speak` — the Quest default, "speak while streaming" is off —
and `streamReply` for HV5), with the real `AudioWorklet` player at 48 kHz like
Quest Browser → OllaBridge Cloud's voice router (master, bench launcher) →
SonicAgent (this branch) with real Piper 1.8, pinned to 2 cores like the
`cpu-basic` Space. Loopback network. Every voice starts in a fresh server
process (cold). Harness: `benchmarks/quest_italian/` (README there).

What the client does today, traced from the code:

| | |
| --- | --- |
| Endpoint | `POST /v1/voice/stream-sessions` (OllaBridge) → WSS `/v1/voice/stream/{id}?ticket=…`, one shared link for STT and TTS |
| Options asked | `output_frame_ms 40`, `flow_control ack`, `tts_queue true`, `chunk_events none` |
| Request | the reply split into phrases (`PhraseSpeechScheduler`: sentence ends, ≥ 24 chars, first phrase ≥ 8), one `tts.speak` per phrase with `voice_id`, up to 12 in flight |
| Audio | PCM16 at the voice's rate (22.05 kHz), 40 ms frames, sequence per phrase |
| Buffering | a jitter buffer per phrase; the first phrase starts after `jitterMs` (120 ms), later ones at once; resampled to the context rate in the page, played by the worklet |
| Flow control | `playback.ack` every 200 ms for every phrase still holding audio; the server keeps ≤ 2000 ms unplayed across the session |
| Interruption | `turn.cancel` target `tts` + local `clear`; the newest turn only (`VoiceTurnController`) |

## Results (medians of 3, ms to the first audible sample)

| Voice | Cold | Warm short · medium · numbers · long | HV5 stream | RTF | Mid-reply gaps (2 cores) | Next reply after stop |
| --- | --- | --- | --- | --- | --- | --- |
| Paola Medium | 1071 | 107 · 296 · 473 · 129 | 355 | 0.056 | none | 99 |
| Serena High | 1680 | 403 · 1298 · 2090 · 576 | 781 | 0.246 | 3 in 2 runs: 627, 261, 45 ms | 404 |
| Aurora Medium | 963 | 125 · 382 · 528 · 185 | 400 | 0.045 | none | 100 |
| Giorgio High | 879 | 94 · 352 · 542 · 166 | 386 | 0.049 | none | 80 |

- First audio is the whole first Piper sentence (Piper yields per sentence): a
  one-sentence 8 s reply waits ~2 s with Serena High.
- After a stop, frames of the old turn stopped arriving at once and the next
  reply started as fast as a warm short reply.
- Phrase joins: 140–350 ms of silence (natural sentence pauses); no phrase edge
  within 29 dB of the phrase level, so no clipped syllables at the seams.

Listening proxy (faster-whisper small, Italian, CER against the text; digits
read as words count as errors):

| Voice | medium | long | Heard |
| --- | --- | --- | --- |
| Paola Medium | 0.125 | 0.07 | clear; "dott. Rossi" garbled |
| Serena High | 0.068 | 0.113 | clearest prosody, questions intoned |
| Aurora Medium | 0.261 | 0.102 | garbled phrases; 10 pauses of 380–870 ms; 40 s for Paola's 26 s (the upstream card: "fa pause enfatiche") |
| Giorgio High | 0.057 | 0.075 | clear, slow (35 s); "dott. Rossi" garbled. A medium-size model (63.5 MB) though published "High": RTF like a medium voice |

Text front end (espeak-ng, the same for every voice): `12,50 €` → "dodici
virgola cinquanta euro", `24/12/2026` → "ventiquattro barra dodici barra…",
`l'1 maggio` → "elle uno maggio", `°C` → "gradi ci", `dott.` ends a sentence.
Times and percentages are fine. Not changed here.

## The change: synthesis runs ahead of pacing

The only gaps came from the server starting the next sentence after the
current one's last frame was sent, with just the 2000 ms budget left on the
client. Now it synthesizes the next sentence, and the next queued phrase's
first sentence, while pacing. Protocol, budget and burst size unchanged.

| | Underruns | Silence mid-reply | Long reply end (29.5 s audio) |
| --- | --- | --- | --- |
| 4 voices × 3 reps, 2 cores, before | 1 (45 ms) — and 2 (627, 261) in an earlier run | | |
| 4 voices × 3 reps, 2 cores, after | 0 | 0 | |
| Serena High, 1 core, before | 30 | ≈ 47 s over 6 long/stream turns | 31.9–46.0 s |
| Serena High, 1 core, after | 1 | 2.1 s | 30.2–32.7 s |

First-audio times did not change beyond run-to-run noise (the one-sentence
"numbers" reply, which the change cannot affect, moved −62…+186 ms between
runs; the 1-core runs shared the machine with other work).

## Which voice

**Giorgio High** for the best balance on this path: clearest transcription,
~95–165 ms warm first audio, no gaps, cheap like a medium model. **Serena High**
sounds best but costs ~5× the CPU: 0.4–2 s first audio, and it relied on the
lookahead to play without gaps on the 2-vCPU Space. **Paola** stays a sound
default. **Aurora** is the weakest (pauses, garbling).

## Still needs a Quest 3

Not measured: Quest Browser's audio output latency and worklet scheduling under
XR load, Wi-Fi jitter and real HF Space round trips, mic → STT on the headset,
listening on the device's speakers. Run the Avatar's `stt-check.html#remote` on
the headset against the Space, record the Quest build, browser version and
network, and compare with the table above.
