# Changelog

All notable changes will be documented here.

## [Unreleased]

### Added
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
- Release signing, an OllaBridge audio route, and a headset measurement.
