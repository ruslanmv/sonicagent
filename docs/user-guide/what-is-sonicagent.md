# What SonicAgent does

SonicAgent transcribes speech and synthesizes a WAV. A product sends one audio file, or one piece of text, and gets one result.

The running conversation is batch:

1. The browser records an utterance, or a client uploads a file.
2. `POST /v1/audio/transcriptions` returns the text.
3. `POST /v1/audio/speech` returns a WAV for a voice in the selected language.
4. Voice Studio plays that WAV from the voice card.

Voice Studio still records, then transcribes, then plays a WAV. A separate realtime socket accepts 20 ms PCM frames, endpoints them, and can speak the first finished phrase before the reply is complete. That socket uses a resume token. The default language model is a local mock until you set `SONIC_LLM_PROVIDER`.

## Words

| Word | Meaning |
| --- | --- |
| Voice Studio | The page at `/` on the voice image and on the Hugging Face Space. |
| STT | Speech to text. Whisper Tiny on CPU. |
| TTS | Text to speech. Piper. |
| Companion / Secretary | Female Piper presets. Companion is slower and softer. Secretary is a little faster and steadier. |
| Bearer token | The `SONIC_API_KEY` required by `/v1/audio/*`. |
| Public demo | An optional, rate-limited anonymous path. Off unless you enable it. |

## What is not ready

The Silero file is not bundled, so endpointing is energy-based until you set `SONIC_VAD_MODEL_PATH`. OllaBridge does not route this audio. No headset run is claimed. See [Production status](../production-status.md).
