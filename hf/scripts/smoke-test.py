"""Call a running SonicAgent voice API.

Examples:
  python hf/scripts/smoke-test.py
  python hf/scripts/smoke-test.py --base-url http://127.0.0.1:8000 --token "$SONIC_API_KEY" --wav tests/fixtures/audio/en_hello.wav
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _request(url: str, *, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get_content_type()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test SonicAgent health and optional transcription")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="")
    parser.add_argument("--wav", type=Path, default=None)
    parser.add_argument("--language", default="en")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")
    status, body, _content_type = _request(f"{base}/health/live")
    print(f"GET /health/live -> {status} {body.decode('utf-8', errors='replace')}")
    if status != 200:
        return 1
    status, body, _content_type = _request(f"{base}/health/ready")
    print(f"GET /health/ready -> {status} {body.decode('utf-8', errors='replace')}")
    if args.wav is None:
        print("No WAV supplied. Readiness above is not a transcription result.")
        return 0 if status == 200 else 1
    if not args.token:
        print("A --token is required to transcribe.", file=sys.stderr)
        return 1
    boundary = "----sonicagentboundary"
    audio = args.wav.read_bytes()
    payload = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language"\r\n\r\n{args.language}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{args.wav.name}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + audio + f"\r\n--{boundary}--\r\n".encode()
    status, body, content_type = _request(
        f"{base}/v1/audio/transcriptions",
        method="POST",
        data=payload,
        headers={
            "Authorization": f"Bearer {args.token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    text = body.decode("utf-8", errors="replace")
    print(f"POST /v1/audio/transcriptions -> {status} {content_type} {text}")
    if status != 200:
        return 1
    parsed = json.loads(text)
    if not isinstance(parsed.get("text"), str):
        print("Response did not include text.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
