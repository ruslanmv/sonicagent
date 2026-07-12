# Binary audio frame

SonicAgent-RT sends microphone and assistant audio as binary WebSocket messages.
For protocol version 1, every binary frame starts with a fixed **24-byte header**.

## Why this matters

The header lets the backend answer basic questions:

- Is this a SonicAgent-RT frame?
- Which protocol version is it?
- Is this input audio or output audio?
- Which audio format is used?
- What sequence number is this?
- How large is the audio payload?

## Version 1 header

| Bytes | Field | Meaning |
| --- | --- | --- |
| 0-1 | Magic | Must be `SA`. |
| 2 | Version | Must be `1`. |
| 3 | Message type | `1` for microphone input, `2` for assistant output. |
| 4 | Codec | `1` for PCM16. Opus is reserved for a future version. |
| 5 | Flags | Small boolean options, such as end-of-utterance. |
| 6-7 | Sample rate | Examples: `16000`, `22050`. |
| 8-11 | Sequence | Frame order number. |
| 12-19 | Timestamp | Timestamp in microseconds. |
| 20-23 | Payload length | Number of audio bytes after the header. |

## Beginner rule

If you are not writing a client library, you normally do not need to build these
frames yourself. Use the browser or Python client helpers.
