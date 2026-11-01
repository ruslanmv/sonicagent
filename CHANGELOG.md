# Changelog

All notable changes will be documented here.

## [Unreleased]

### Fixed
- Speech-only stream: `SONIC_MAX_OUTBOUND_QUEUE_MS` counted every frame ever sent and never subtracted, so with the default 2000 ms every Piper reply longer than two seconds ended in `rate_limited` after exactly 100 frames. It now bounds unplayed audio and paces instead of refusing (HV3).
- Speech-only stream: recognition and synthesis no longer share one slot (an utterance during her speech was refused); a cancel frees the slot at once; input frames at the wrong sample rate, with an odd byte count or longer than 200 ms are refused with the reason (HV3).

### Added
- Speech-only stream `stream_options` (HV3), all off by default: `chunk_events: none`, `output_frame_ms: 40`, `flow_control: ack` with `playback.ack`, `endpointing: client` (one `transcript.final` per commit, with `commit_seq`), `tts_queue`. `turn.cancel` takes an optional `target`. Capabilities add `streaming.stt_ready`/`tts_ready`. `python -m benchmarks.stream.overhead` measures framing cost.
- Speech-only stream at `POST /v1/audio/stream-sessions` and `WS /v1/audio/stream/{session_id}`. It transcribes with endpointed faster-whisper and speaks Piper sentence by sentence. It does not call the language model and it does not emit partial transcripts.
- Batch speech to text with faster-whisper Tiny on CPU, for English, Spanish, French, German, Italian, and Portuguese.
- Batch Piper speech for the `hp-piper-voices` mirror, including Companion and Secretary presets.
- Voice Studio on the `hf/` image and the Hugging Face Space `ruslanmv/SonicAgent`.
- Voice Studio Speak panel can download the generated WAV. The server does not keep that file.
- An HTTP endpoint probe and one published CPU Basic measurement.
- Authenticated realtime turns: resume token, one live socket, sequence checks, energy endpointing, optional pinned Silero file, phrase PCM, barge-in cancellation, and OpenAI-compatible or Ollama streaming with one retry.
- Browser PCM helpers for resampling, 20 ms frames, bounded playback, and clearing audio on cancel.
- In-process realtime counters on `/metrics`. `scripts/export-sbom.sh` writes an unsigned CycloneDX file when the tool is installed.

### Still open
- The Silero ONNX file is not bundled. The default language model is still the local mock.
- Release signing and an OllaBridge audio route. Moonshine, Nemotron, and Pocket TTS are not installed. One Quest 3 browser measurement covers local Whisper Tiny only.
