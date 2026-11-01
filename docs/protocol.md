## API overview

### Create a session

```http
POST /v1/sessions
Content-Type: application/json
```

```json
{
  "language": "it",
  "voice_id": "it_IT-paola-medium",
  "input_audio": {
    "codec": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1,
    "frame_ms": 20
  },
  "client_capabilities": {
    "binary_audio": true,
    "barge_in": true,
    "partial_transcripts": false
  }
}
```

Example response:

```json
{
  "session_id": "ses_example",
  "resume_token": "example-resume-token",
  "websocket_url": "/v1/realtime/ses_example",
  "expires_at": "2026-07-10T18:00:00Z",
  "server_capabilities": {
    "binary_audio": true,
    "barge_in": true,
    "partial_transcripts": false,
    "phrase_pipelined_tts": true
  },
  "output_audio": {
    "codec": "pcm_s16le",
    "sample_rate": 22050,
    "channels": 1
  }
}
```

### Speech-only WebSocket

`POST /v1/audio/stream-sessions` creates a session that does not call the language model. The socket is `/v1/audio/stream/{session_id}?resume_token=...`. Protocol `sonic-speech-stream-v1`. faster-whisper on this socket is endpointed, so partial transcripts are not sent. Piper output is one PCM16 buffer per sentence. Field list: [Speech-only stream](api/speech-stream.md).

### WebSocket

```text
/v1/realtime/{session_id}?resume_token=...
```

This socket is the full turn. It can call the language model. A client that already owns the conversation uses the speech-only socket above.

Client control events:

- `session.update`
- `input_audio.commit`
- `input_audio.clear`
- `response.cancel`
- `call.end`
- `ping`

Server events:

- `session.created`
- `session.updated`
- `speech.started`
- `speech.stopped`
- `transcript.partial`
- `transcript.final`
- `response.created`
- `response.text.delta`
- `response.text.done`
- `response.audio.started`
- `response.audio.done`
- `response.cancelled`
- `metrics.turn`
- `warning`
- `error`
- `pong`

## Binary audio frame v1

Binary audio uses a 24-byte big-endian header. The golden fixture is `tests/golden/protocol/binary-frame-v1.hex`.

| Offset | Size | Field |
|---:|---:|---|
| 0 | 2 | Magic bytes `SA` |
| 2 | 1 | Protocol version |
| 3 | 1 | Message type |
| 4 | 1 | Codec |
| 5 | 1 | Flags |
| 6 | 2 | Sample rate |
| 8 | 4 | Sequence number |
| 12 | 8 | Timestamp in microseconds |
| 20 | 4 | Payload length |
| 24 | N | Audio payload |

Message types: `0x01` microphone audio, `0x02` synthesized audio. Codec `0x01` is PCM S16LE. Opus is reserved for a later protocol version.

See [`docs/api/binary-frame.md`](docs/api/binary-frame.md) and the Python/TypeScript contract tests.

