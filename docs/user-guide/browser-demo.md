# Use the browser demo

The browser demo is the easiest way to see how SonicAgent-RT is intended to feel.
It is currently a development demo, not a finished product.

## Open the page

1. Start the app with `make run`.
2. Open `http://localhost:5173` in a modern browser.
3. Use a local development machine when possible. Microphone permissions and
audio behavior vary by browser and operating system.

## What the finished demo should show

The product goal is a clear voice-assistant dashboard with:

- Connection status.
- Microphone status.
- Listening, thinking, speaking, interrupted, and error states.
- Transcript timeline.
- Assistant audio playback.
- Voice and language settings for English and Italian profiles.
- Latency information for each turn.
- A clear recovery path when something fails.

## Current limitations

The current repository still contains unfinished browser and backend paths.
If the page starts but no complete voice conversation works, check
[Production status](../production-status.md). Use deterministic tests and smoke
checks to verify what is implemented today.
