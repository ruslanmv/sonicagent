"""Command-line entry point."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="sonicagent-rt")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only in minimal/offline installs.
        raise SystemExit(
            "uvicorn is not installed. Run `make install` with access to the approved Python package mirror "
            "or install the `sonicagent-rt` runtime dependencies before starting the server."
        ) from exc

    uvicorn.run("sonicagent_rt.app:app", host=args.host, port=args.port, reload=args.reload)
