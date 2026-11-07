"""Keep the SonicAgent Space awake, and bring it back when it is down.

Why this exists. SonicAgent runs on a free ``cpu-basic`` Hugging Face Space,
and a free Space goes to sleep after 48 hours without a request
(``gcTimeout: 172800``). While it sleeps, OllaBridge Cloud answers every
``/v1/voice/*`` call with 503 ("the speech service is starting"). That is
exactly what HomePilot Avatar showed on 2026-11-07, as "SonicAgent could not
start", until the Space was restarted by hand.

The scheduled workflow ``.github/workflows/space-keepalive.yml`` runs this a
few times a day:

* **RUNNING and ready**: the ``/health/ready`` request is itself the traffic
  that resets the sleep timer, so there is nothing more to do.
* **SLEEPING**: wake it with a request to its own address and the Hub's
  restart API, then wait until ``/health/ready`` answers.
* **RUNNING but not ready, or RUNTIME_ERROR**: restart through the Hub API,
  then wait.
* **BUILDING / APP_STARTING**: wait.
* **BUILD_ERROR / CONFIG_ERROR / NO_APP_FILE**: a restart cannot fix a broken
  build. Fail loudly so GitHub emails the owner, and leave a redeploy to a
  person.
* **PAUSED / STOPPED**: the owner chose this. Leave it alone unless the run
  was started with ``--force``.

It needs only the standard library and an ``HF_TOKEN`` with write access to
the Space. The token is sent only to huggingface.co and is never printed.
Exit codes: 0 ready (or paused by choice), 1 still not ready, 2 bad
configuration.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HUB = "https://huggingface.co"
WAITING = {"BUILDING", "RUNNING_BUILDING", "APP_STARTING", "RUNNING_APP_STARTING"}
BROKEN = {"BUILD_ERROR", "CONFIG_ERROR", "NO_APP_FILE"}
CHOSEN_OFF = {"PAUSED", "STOPPED"}


def decide(stage: str | None, ready: bool, *, force: bool = False) -> str:
    """What to do for a Space in ``stage`` whose ``/health/ready`` answered ``ready``.

    Returns one of ``ok``, ``wake``, ``restart``, ``wait``, ``broken`` or
    ``paused``. Pure; the tests pin every row.
    """
    s = (stage or "").upper()
    if s in CHOSEN_OFF:
        return "restart" if force else "paused"
    if s in BROKEN:
        return "broken"
    if s == "SLEEPING":
        return "wake"
    if s in WAITING:
        return "wait"
    if s == "RUNTIME_ERROR":
        return "restart"
    if s == "RUNNING":
        return "ok" if ready else "restart"
    # An unknown stage (the Hub adds them): if the app answers, it is fine; otherwise restart.
    return "ok" if ready else "restart"


def space_url(runtime: dict, repo_id: str) -> str:
    """The Space's own address: the Hub's first ready domain, else the conventional one."""
    for d in runtime.get("domains") or []:
        if d.get("domain") and d.get("stage", "READY") == "READY":
            return "https://" + d["domain"]
    owner, _, name = repo_id.partition("/")
    return f"https://{owner}-{name}".lower().replace("_", "-").replace(".", "-") + ".hf.space"


def _request(url: str, *, token: str | None = None, method: str = "GET", timeout: float = 30.0):
    headers = {"User-Agent": "sonicagent-keepalive"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method=method, headers=headers, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, str(e).encode()


def runtime_of(repo_id: str, token: str) -> dict:
    status, body = _request(f"{HUB}/api/spaces/{repo_id}/runtime", token=token)
    if status != 200:
        raise RuntimeError(f"Hub runtime query answered HTTP {status}")
    return json.loads(body or b"{}")


def is_ready(base: str) -> bool:
    status, body = _request(base + "/health/ready", timeout=45.0)
    if status != 200:
        return False
    try:
        return bool(json.loads(body).get("ready"))
    except (ValueError, AttributeError):
        return False


def restart(repo_id: str, token: str) -> int:
    status, _ = _request(f"{HUB}/api/spaces/{repo_id}/restart", token=token, method="POST")
    return status


def run(
    repo_id: str,
    token: str,
    *,
    force: bool = False,
    wait_s: int = 600,
    sleep=time.sleep,
    clock=time.monotonic,
) -> int:
    rt = runtime_of(repo_id, token)
    stage = rt.get("stage")
    base = space_url(rt, repo_id)
    ready = is_ready(base) if stage not in CHOSEN_OFF else False
    if stage == "RUNNING" and not ready:
        # One slow answer is not an outage: give the app a second chance before restarting it.
        sleep(20)
        ready = is_ready(base)
    action = decide(stage, ready, force=force)
    print(f"space={repo_id} stage={stage} ready={ready} action={action} url={base}")

    if action == "ok":
        return 0
    if action == "paused":
        print("The Space is paused by its owner; leaving it alone (run with force to override).")
        return 0
    if action == "broken":
        print(f"::error::The Space is in {stage}; a restart cannot fix a broken build. Redeploy it.")
        return 1
    if action == "wake":
        _request(base + "/health/live", timeout=60.0)  # a request to a sleeping Space starts it
        status = restart(repo_id, token)
        print(f"woke the Space (restart API answered HTTP {status})")
    elif action == "restart":
        status = restart(repo_id, token)
        print(f"restarted the Space (restart API answered HTTP {status})")
        if status not in (200, 202):
            print(f"::warning::The restart API answered HTTP {status}; the token needs write access.")

    return wait_ready(repo_id, token, base, wait_s, sleep=sleep, clock=clock)


def wait_ready(
    repo_id: str, token: str, base: str, wait_s: int, *, sleep=time.sleep, clock=time.monotonic
) -> int:
    deadline = clock() + wait_s
    while clock() < deadline:
        sleep(15)
        if is_ready(base):
            print("The Space is ready.")
            return 0
    print(
        f"::error::The Space was not ready after {wait_s} s (stage now {runtime_of(repo_id, token).get('stage')})."
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Keep the SonicAgent Space awake; restart it when it is down"
    )
    parser.add_argument("--repo-id", default=None, help="owner/name; default HF_USERNAME/SPACE_NAME")
    parser.add_argument(
        "--force", action="store_true", help="restart even a paused Space, or one that looks fine"
    )
    parser.add_argument(
        "--wait", type=int, default=600, help="seconds to wait for /health/ready after acting"
    )
    args = parser.parse_args(argv)

    token = os.environ.get("HF_TOKEN", "").strip()
    repo_id = args.repo_id or "/".join(
        x for x in (os.environ.get("HF_USERNAME", "").strip(), os.environ.get("SPACE_NAME", "").strip()) if x
    )
    if not token or "/" not in repo_id:
        print("HF_TOKEN and HF_USERNAME/SPACE_NAME (or --repo-id) are required.", file=sys.stderr)
        return 2
    if args.force:
        # A person asked for a restart: do it whatever the stage (paused included), then wait.
        # Waiting goes straight to /health/ready — re-running the decision right after a restart
        # would see RUNNING-but-not-ready and restart it a second time.
        base = space_url(runtime_of(repo_id, token), repo_id)
        print(f"forced restart of {repo_id}: restart API answered HTTP {restart(repo_id, token)}")
        return wait_ready(repo_id, token, base, args.wait)
    return run(repo_id, token, wait_s=args.wait)


if __name__ == "__main__":
    sys.exit(main())
