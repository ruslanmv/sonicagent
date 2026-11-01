# Security and privacy

SonicAgent-RT handles microphone audio and generated text. Treat both as private
unless the user clearly agrees otherwise.

## Development safety

Do not expose the local development server to the public internet. Development
settings are for local testing only.

## Threat model

Untrusted input is microphone audio, uploaded files, text sent to speech, model files, and the language-model response.

| Boundary | What the process does |
| --- | --- |
| Batch and session routes | Bearer token. Placeholder tokens are rejected. Origin is checked when the browser sends one. |
| Realtime socket | A random resume token. One live socket per session. Reconnect uses the same token after the first socket closes. Sequence numbers must increase. |
| Audio and text | Size and duration caps. Frames over 64 KiB are rejected. The outbound queue stops a turn when it exceeds the configured milliseconds. |
| Logs and metrics | No transcript text, no resume token, no API key. LLM failures log the error type and model name. |
| Storage | Audio and transcripts stay off unless the operator turns the store flags on. |
| Models | Piper files are checked against `voices.json`. Silero runs only when the file matches the pinned sha256. |

TLS is terminated in front of the process. This repository does not sign release artifacts. `scripts/export-sbom.sh` writes a CycloneDX file when `cyclonedx-py` is installed.

## Required production controls

Before production use, implement and verify:

- HTTPS/TLS for all browser and API traffic.
- Secure WebSocket connections.
- Short-lived session tokens.
- Browser origin allowlists.
- Request-size and audio-frame-size limits.
- Rate limits and concurrency limits.
- Redacted logs.
- Opt-in audio/transcript storage.
- Dependency, container, license, secret, and SBOM scanning.
- Threat-model review for untrusted audio, text, model files, and provider output.

## Simple privacy defaults

Recommended defaults:

| Data | Default |
| --- | --- |
| Audio storage | Off |
| Transcript storage | Off |
| Transcript logging | Off |
| Secrets in logs | Never |

## If you are unsure

Keep the service local, use fake providers, and do not process private audio.
