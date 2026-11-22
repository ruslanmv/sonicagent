"""Deploy this checkout to the `ruslanmv/SonicAgent` Space from a session, safely.

The canonical deploy is `.github/workflows/huggingface-space.yml` on a push to main/master. Use
this to try a branch on the live Space before merging (as done for PR #86), with the same two
steps the workflow runs (`prepare-space.py`, then `upload-space.py`), plus what a person needs
around them:

  - preview: files NEW / CHANGED / DELETED against the live Space (upload-space.py mirrors the
    staged tree, so a stale remote file IS deleted; read the list before pushing);
  - the live Space commit, printed as the ROLLBACK point (re-deploy that revision to undo);
  - after --push: wait for the build (BUILD_ERROR / RUNTIME_ERROR end it), then a smoke test:
    /health/live, Voice Studio's asset version, the catalog's voices for --locale, each voice's
    preview WAV, and `/v1/voices` reporting them installed.

Synthesis is not smoke-tested: the public demo is off on the Space (`/demo/speech` answers 403)
and the service key is a Space secret. Test speech in Voice Studio's token mode.

    HF_TOKEN=... python hf/scripts/space-deploy.py                     # preview only
    HF_TOKEN=... python hf/scripts/space-deploy.py --push --check it_IT-aurora-medium it_IT-giorgio-high
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPACE = "ruslanmv/SonicAgent"
URL = "https://ruslanmv-sonicagent.hf.space"


def get(path: str, timeout: int = 30) -> bytes:
    with urllib.request.urlopen(URL + path, timeout=timeout) as r:  # noqa: S310 - fixed host
        return r.read()


def smoke(voices: list[str]) -> bool:
    ok = True
    print("health:", get("/health/live").decode().strip())
    page = get("/").decode("utf-8", "replace")
    print("ui asset version:", [p for p in ("app.js?v=" + str(n) for n in range(1, 50)) if p in page])
    catalog = json.loads(get("/ui-assets/catalog.json"))
    listed = {v["id"] for loc in catalog["locales"] for v in loc["voices"]}
    installed = {v["id"]: v.get("installed") for v in json.loads(get("/v1/voices")).get("voices", [])}
    for vid in voices:
        try:
            wav = len(get(f"/ui-assets/examples/{vid}.wav"))
        except Exception as exc:  # noqa: BLE001 - report every failure, keep checking
            wav = f"error {exc}"
        good = vid in listed and installed.get(vid) is True and isinstance(wav, int)
        ok &= good
        print(f"  {vid}: in catalog={vid in listed} installed={installed.get(vid)} preview={wav}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--check", nargs="*", default=[], help="voice ids to smoke-test after the build")
    a = ap.parse_args()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("HF_TOKEN is not set", file=sys.stderr)
        return 1
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=token)
    stage = Path(tempfile.mkdtemp(prefix="space-stage-"))
    subprocess.run(
        [sys.executable, str(ROOT / "hf/scripts/prepare-space.py"), "--dest", str(stage)], check=True
    )
    rollback = api.space_info(SPACE).sha
    remote = set(api.list_repo_files(SPACE, repo_type="space"))
    local = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    changed = []
    cache = Path(tempfile.mkdtemp(prefix="space-remote-"))
    for f in sorted(local & remote):
        if f.endswith(".wav"):
            continue
        r = hf_hub_download(SPACE, f, repo_type="space", token=token, local_dir=cache)
        if Path(r).read_bytes() != (stage / f).read_bytes():
            changed.append(f)
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout
    print(f"checkout {head.strip()}  →  Space {SPACE}")
    print(f"ROLLBACK point (live Space commit): {rollback}")
    print("NEW:", sorted(local - remote))
    print("CHANGED:", changed)
    print("DELETED:", sorted(p for p in remote - local if p != ".gitattributes"))
    if not a.push:
        print("preview only: nothing uploaded (add --push)")
        return 0
    env = dict(
        os.environ, HF_USERNAME=SPACE.split("/")[0], SPACE_NAME=SPACE.split("/")[1], GITHUB_SHA=head.strip()
    )
    subprocess.run(
        [sys.executable, str(ROOT / "hf/scripts/upload-space.py"), "--dest", str(stage)], check=True, env=env
    )
    print("new Space commit:", api.space_info(SPACE).sha)
    last = None
    for i in range(120):  # up to 20 minutes
        stage_now = api.get_space_runtime(SPACE).stage
        if stage_now != last:
            print(time.strftime("%T"), stage_now, flush=True)
            last = stage_now
        if stage_now in ("BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"):
            print(f"build failed; roll back by re-deploying {rollback}", file=sys.stderr)
            return 1
        if stage_now == "RUNNING" and i > 3:
            break
        time.sleep(10)
    return 0 if smoke(a.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
