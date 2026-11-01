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

`turn.cancelled` includes `clear_audio: true`.

`SONIC_MAX_OUTBOUND_QUEUE_MS` bounds audio sent and **not yet played**. When the client is that far ahead, the server waits before sending the next frame; it does not end the turn. Without acknowledgements, "played" is estimated as wall-clock time since the first frame. Before HV3 the counter added every frame ever sent and never subtracted, so with the default 2000 ms every reply longer than two seconds ended in `rate_limited` ("outbound audio queue is full") after exactly 100 frames. A value of `0` still refuses at once, as it always did.

## Negotiated options (HV3)

`POST /v1/audio/stream-sessions` accepts an optional `stream_options` object. Omit it and the session is the v1 behaviour above, byte for byte. Unknown keys and values are refused with 400 rather than ignored. The response and `session.ready` echo the options in force as `options`, and the response lists `options_supported`.

| Option | Values (first = v1) | Effect |
| --- | --- | --- |
| `chunk_events` | `all`, `none` | `none` drops the JSON `tts.audio.chunk` before each binary frame. The 24-byte header already carries sequence, rate and timestamp, and a session speaks one phrase at a time, so frames between `tts.audio.meta` and `tts.audio.done` belong to that `turn_id`. |
| `output_frame_ms` | `20`, `40` | Length of each output frame. `tts.audio.meta` carries `frame_ms`. |
| `flow_control` | `none`, `ack` | `ack`: the client sends `{"type":"playback.ack","turn_id","played_ms"}` and the server keeps at most `SONIC_MAX_OUTBOUND_QUEUE_MS` of unplayed audio in flight. If playback does not move for 10 s the turn ends with `rate_limited` ("client stopped acknowledging playback"). |
| `endpointing` | `server`, `client` | `client`: the VAD only reports `speech.started`; audio is held until the end-of-utterance flag and transcribed once. Each commit produces exactly one `transcript.final`, carrying the `commit_seq` of the committing frame, with `text: ""` and `no_speech: true` when nothing was held. A commit that arrives while another is transcribing waits (up to two), instead of being refused. |
| `tts_queue` | `false`, `true` | `true`: `tts.speak` while a phrase is playing is queued (`tts.queued`, up to 16) and spoken in order, each with its own `tts.audio.done`. A cancel clears the queue. |

Measured per second of Piper speech with the real encoder (`python -m benchmarks.stream.overhead`):

| framing | Piper rate | messages/s | bytes/s | overhead |
| --- | --- | --- | --- | --- |
| v1 default | 22050 Hz | 100 | 54250 | 18.71% |
| no chunk events | 22050 Hz | 50 | 45300 | 2.65% |
| 40 ms, no chunk events | 22050 Hz | 25 | 44700 | 1.34% |
| v1 default | 16000 Hz | 100 | 42150 | 24.08% |
| no chunk events | 16000 Hz | 50 | 33200 | 3.61% |
| 40 ms, no chunk events | 16000 Hz | 25 | 32600 | 1.84% |

### Also changed for every session

- **Recognition and synthesis have separate slots.** In `duplex_speech` an utterance spoken while she is talking is transcribed; before, it was refused as "a speech turn is already running".
- **`turn.cancel` frees the slot at once**, so the `tts.speak` that follows a barge-in is accepted. It takes an optional `target` of `all` (default, the v1 meaning), `tts` or `stt`, echoed in `turn.cancelled`.
- **Input frames are checked against what the server decodes.** A frame whose `sample_rate` is not `SONIC_INPUT_SAMPLE_RATE`, a payload with an odd byte count, or a frame longer than 200 ms is `invalid_audio` with the reason. A 48 kHz frame used to be transcribed as if it were 16 kHz.
- Additive fields: `audio.input.committed.commit_seq`, `transcript.final.audio_ms`, `tts.audio.done.audio_ms`, `metrics.turn.audio_ms`, and on capabilities `streaming.stt_ready`, `streaming.tts_ready`, `streaming.input_sample_rate`, `streaming.options_supported`. `streaming.available` says the socket exists; `stt_ready` says a turn would work now. A sleeping Space is available and not ready.

## Capabilities

`GET /v1/audio/capabilities` keeps the existing `stt`, `tts`, `realtime`, and `route` objects. It adds `streaming`, `stt_providers`, and `tts_providers`.

`moonshine-streaming`, `nemotron-stream`, and `pocket-tts-stream` are present with `ready: false` and `reason: "not-installed"`. Moonshine is English-only in that report. Do not treat a false provider as a loaded model.
