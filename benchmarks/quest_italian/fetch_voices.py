"""Download registry voices into a SonicAgent model cache, SHA-256 checked.

Mirror (`source.base_url`) first; on HTTP 404 the voice's pinned `fallback_urls`, exactly as
`hf/scripts/setup-models.py` does. Prints which source served each file, so a run also tells
you whether the `ruslanmv/hp-piper-voices` mirror has the file yet.

    python benchmarks/quest_italian/fetch_voices.py --cache /tmp/sa-cache \
        it_IT-paola-medium it_IT-serena-high it_IT-aurora-medium it_IT-giorgio-high it_IT-riccardo-x_low
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "model_registry" / "voices.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="SONIC_MODEL_CACHE_DIR (files go to <cache>/tts)")
    ap.add_argument("voices", nargs="+")
    a = ap.parse_args()
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    base = reg["source"]["base_url"].rstrip("/")
    out = Path(a.cache) / "tts"
    out.mkdir(parents=True, exist_ok=True)
    by_id = {v["id"]: v for v in reg["voices"]}
    for vid in a.voices:
        v = by_id[vid]
        fallback = v.get("fallback_urls") or []
        files = [(v["model_path"], v["model_sha256"]), (v["config_path"], v["config_sha256"])]
        for i, (rel, sha) in enumerate(files):
            dest = out / Path(rel).name
            if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == sha:
                print(f"{vid}: cached {dest.name}")
                continue
            source = "mirror"
            try:
                data = urllib.request.urlopen(f"{base}/{rel}", timeout=300).read()  # noqa: S310
            except urllib.error.HTTPError as exc:
                if exc.code != 404 or len(fallback) <= i:
                    raise
                source = "fallback"
                data = urllib.request.urlopen(fallback[i], timeout=300).read()  # noqa: S310
            if hashlib.sha256(data).hexdigest() != sha:
                raise SystemExit(f"{vid}: checksum mismatch for {rel} from {source}")
            dest.write_bytes(data)
            print(f"{vid}: {source} {dest.name} {len(data)} bytes")


if __name__ == "__main__":
    main()
