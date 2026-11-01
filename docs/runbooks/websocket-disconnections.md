# WebSocket disconnections

A dropped realtime socket cancels the active turn and releases the session so the same resume token can connect again.

## What you should see

- The first connection receives `session.created` with `resumed: false`.
- A second connection while the first is open is closed with code 1008.
- After the first socket closes, the next connection receives `session.updated` with `resumed: true`.
- Input sequence numbers start again at the client's first frame. A gap or replay returns `invalid_audio`.
- `response.cancelled` with `clear_audio: true` means the browser must drop queued playback.

## Checks

1. `GET /health/ready` shows whether Whisper is loaded. Live health does not.
2. Confirm the client is sending the resume token as a query parameter and not writing it to a log.
3. Confirm only one tab holds the session.
4. If turns pile up, read `sonicagent_realtime_inflight` on `/metrics`. It has no transcript labels.

## What this is not

A disconnect is not a headset failure report. The browser AudioWorklet page and Voice Studio are different clients.
