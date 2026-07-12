# WebSocket events

The WebSocket is the live connection used during a voice conversation.

It carries two kinds of messages:

1. **Binary audio frames** for microphone and assistant audio.
2. **JSON events** for state changes, transcripts, text deltas, cancellation,
   errors, and metrics.

## Common JSON events

| Event | Direction | Meaning |
| --- | --- | --- |
| `session.created` | Server to client | The realtime session is ready. |
| `speech.started` | Server to client | The server detected user speech. |
| `speech.stopped` | Server to client | The server detected the end of user speech. |
| `transcript.final` | Server to client | Final speech-to-text result for an utterance. |
| `response.text.delta` | Server to client | A piece of assistant text. |
| `response.audio.started` | Server to client | Assistant audio output started. |
| `response.audio.done` | Server to client | Assistant audio output finished. |
| `response.cancel` | Client to server | User wants to stop the current response. |
| `response.cancelled` | Server to client | The server cancelled active response work. |
| `error` | Server to client | Something failed. |

## Beginner rule

A normal user does not need to read WebSocket events directly. They are mainly
for developers building browser, mobile, or Python clients.
