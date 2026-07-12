# What SonicAgent-RT does

SonicAgent-RT helps a computer talk and listen in near real time.

A typical conversation looks like this:

1. Your browser records microphone audio.
2. The browser sends small audio frames to the SonicAgent-RT backend.
3. The backend checks the audio format and order.
4. Voice activity detection decides when you started and stopped speaking.
5. Speech-to-text turns your voice into text.
6. A text model writes the assistant response.
7. Text-to-speech turns the response into audio.
8. The backend streams assistant audio back to the browser.

## Important words in simple language

| Word | Simple meaning |
| --- | --- |
| Backend | The server program that does most of the work. |
| Browser demo | The web page you use to test a voice conversation. |
| WebSocket | A live network connection between browser and backend. |
| PCM16 | A common uncompressed audio format. |
| VAD | Voice activity detection; it decides whether audio contains speech. |
| STT | Speech-to-text. |
| LLM | The AI text model that writes a reply. |
| TTS | Text-to-speech. |
| Fake provider | A deterministic test provider that works without real AI models. |

## What works today

The repository currently includes tested protocol helpers, audio-buffering
building blocks, deterministic fake-provider smoke checks, and a web-client test
suite.

## What is not ready yet

Real production use still requires the missing provider implementations,
validated model downloads, green non-skipped test coverage, and a successful
backend run with all runtime dependencies installed. See
[Production status](../production-status.md).
