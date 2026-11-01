# Changelog

All notable changes will be documented here.

## [Unreleased]

### Added
- Batch speech to text with faster-whisper Tiny on CPU, for English, Spanish, French, German, Italian, and Portuguese.
- Batch Piper speech for the `hp-piper-voices` mirror, including Companion and Secretary presets.
- Voice Studio on the `hf/` image and the Hugging Face Space `ruslanmv/SonicAgent`.
- Voice Studio Speak panel can download the generated WAV. The server does not keep that file.
- An HTTP endpoint probe and one published CPU Basic measurement.

### Still open
- Realtime WebSocket turns, Silero VAD, barge-in, and a streaming language model.
