# What SonicAgent does

SonicAgent transcribes speech and synthesizes a WAV. A product sends one audio file, or one piece of text, and gets one result.

The running conversation is batch:

1. The browser records an utterance, or a client uploads a file.
2. `POST /v1/audio/transcriptions` returns the text.
3. `POST /v1/audio/speech` returns a WAV for a voice in the selected language.
4. Voice Studio plays that WAV from the voice card.

A streaming call (small PCM frames, voice activity detection, a live language model, and audio that starts before the sentence is finished) is the later design. It is not what the server does today.

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

Realtime WebSocket turns, Silero voice activity detection, barge-in, and a streaming language model. See [Production status](../production-status.md).
