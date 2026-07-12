# Security and privacy

SonicAgent-RT handles microphone audio and generated text. Treat both as private
unless the user clearly agrees otherwise.

## Development safety

Do not expose the local development server to the public internet. Development
settings are for local testing only.

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
