## Security baseline

Before production deployment, complete the controls described in [`SECURITY.md`](SECURITY.md) and [`docs/security.md`](docs/security.md):

- TLS termination and secure WebSocket transport.
- Short-lived, audience-bound session tokens.
- Origin allowlist and authenticated session creation.
- Bounded payload size, frame rate, session duration, and concurrent sessions.
- Per-tenant isolation and rate limiting.
- No shell interpolation for model or provider arguments.
- Dependency, container, license, secret, and SBOM scanning.
- Redacted logs and opt-in storage.
- Threat-model review for untrusted audio, text, model files, and provider output.

The scaffold development token is not safe for public networks.

