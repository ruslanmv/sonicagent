# Troubleshooting basics

This page lists common problems in plain language.

## `make install` warns about missing runtime dependencies

Meaning: the local package was installed, but Python packages needed to run the
backend are missing.

Fix:

1. Connect to your approved Python package mirror.
2. Install the project runtime dependencies.
3. Run `make install` again.

## `make run` says `uvicorn is not installed`

Meaning: the backend web server package is missing.

Fix: install runtime dependencies from an approved package mirror. The browser
dev server may still start, but the API backend will not be available until
`uvicorn` is installed.

## Voice Studio does not transcribe

Open the voice image or the Space, not `http://localhost:5173`. That second page is the unfinished realtime client.

Check `GET /health/ready`. Live health only means the process is up. The public demo transcribes only when `SONIC_PUBLIC_DEMO_ENABLED` is true. Otherwise the page needs the bearer token.

## Tests pass but show skipped tests

The skipped tests are the realtime modules that are not built yet. Batch speech tests are separate. See [Production status](production-status.md).

## Real model downloads fail

Meaning: the model registry, network, cache path, or checksums may not be ready.
Do not bypass checksum or attribution checks for production use.

## I am not an IT expert. What should I send when asking for help?

Copy and paste:

- The command you ran.
- The complete error message.
- Your operating system.
- Python version: `python --version`.
- Node version: `node --version`.
- Whether you are using a company package mirror or offline environment.
