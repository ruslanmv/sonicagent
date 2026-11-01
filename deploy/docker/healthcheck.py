import os
import urllib.request

port = os.environ.get("PORT") or os.environ.get("SONIC_PORT") or "8000"
url = f"http://127.0.0.1:{port}/health/live"
with urllib.request.urlopen(url, timeout=2) as response:
    raise SystemExit(0 if response.status == 200 else 1)
