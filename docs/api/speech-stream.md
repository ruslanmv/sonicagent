# Speech-only stream

`/v1/realtime/{id}` runs a full turn: endpointed audio, speech to text, SonicAgent's language model, then Piper. Avatar clients that already own the conversation must not open that socket.

The speech-only socket transcribes and speaks. It does not call the language model.

## Session

```http
POST /v1/audio/stream-sessions
Authorization: Bearer <service credential>
```

```json
{
  "mode": "stt_only",
  "language": "it",
  "voice_id": "it_IT-paola-medium",
  "stt_provider": "faster-whisper"
}
```

`mode` is `stt_only`, `tts_only`, or `duplex_speech`. The response carries a random `resume_token` and `websocket_url`. The service credential is not placed in that URL.

`faster-whisper` is the installed provider. Its `streaming_mode` is `endpointed` and `partial_results` is false. `moonshine-streaming` is rejected because that checkpoint is not installed. Italian stays on faster-whisper.

## Socket

```text
/v1/audio/stream/{session_id}?resume_token=...
```

The first message is `session.ready` with `llm: false` and `partial_results: false`. One live socket may hold the token. A second socket is closed with 1008 until the first disconnects.

Microphone input reuses the 24-byte PCM16 frame. Mono, 16 kHz, 20 ms frames. A skipped sequence returns `session.error` and does not invent the missing audio. Opus is not decoded.

Client events:

- `ping`
- `turn.cancel`
- `session.close`
- `tts.speak` with `text` and optional `turn_id`

`tts.speak` is rejected on `stt_only`. Binary audio is rejected on `tts_only`.

Server events:

- `session.ready`
- `audio.input.started`
- `audio.input.committed`
- `speech.started`
- `speech.stopped`
- `transcript.final`
- `tts.started`
- `tts.audio.meta`
- `tts.audio.chunk`
- `tts.audio.done`
- `turn.cancelled`
- `session.error`
- `session.closed`
- `metrics.turn`
- `pong`

`transcript.partial` is not sent. A completed utterance produces one `transcript.final`. `metrics.turn` sets `llm` to false.

## Audio out

Piper's sentence iterator yields one PCM16 buffer per sentence. The socket sends `tts.audio.meta` with `incremental: "sentence"` on the first buffer, then JSON `tts.audio.chunk` plus a binary output frame for each 20 ms piece. Later sentences are synthesized after the earlier buffer has been handed to the socket. This is not sample-level or token-level streaming.

`turn.cancelled` includes `clear_audio: true`. The outbound queue stops when queued audio would exceed `SONIC_MAX_OUTBOUND_QUEUE_MS`.

## Capabilities

`GET /v1/audio/capabilities` keeps the existing `stt`, `tts`, `realtime`, and `route` objects. It adds `streaming`, `stt_providers`, and `tts_providers`.

`moonshine-streaming`, `nemotron-stream`, and `pocket-tts-stream` are present with `ready: false` and `reason: "not-installed"`. Moonshine is English-only in that report. Do not treat a false provider as a loaded model.
