"""Bench-only OllaBridge Cloud launcher: the real app and voice router.

Only the caller lookup is replaced, so the fixed bearer token ``bench-device-token``
resolves to one bench user without a pairing database. Never deploy this.

    python ollabridge_bench.py            # env: OB_PORT (8702), OLLAMBRIDGE_VOICE_* , CORS_ORIGINS
"""

from __future__ import annotations

import os

import uvicorn
from ollabridge_cloud.api import voice_bridge


def _bench_user(request) -> str | None:
    auth = request.headers.get("authorization") or ""
    return "bench-user" if auth == "Bearer bench-device-token" else None


voice_bridge.resolve_request_user_id = _bench_user

from ollabridge_cloud.main import app  # noqa: E402  (after the patch, on purpose)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("OB_PORT", "8702")), log_level="warning")
