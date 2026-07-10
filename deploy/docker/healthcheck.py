import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/health/live", timeout=2) as response:
    raise SystemExit(0 if response.status == 200 else 1)
