"""Download the pinned multilingual Whisper checkpoint into the model cache.

Optional Piper voices are downloaded only with ``--tts``. The file list is
every voice in ``model_registry/voices.json``, hosted on
``ruslanmv/hp-piper-voices``. Files are not loaded unless ``SONIC_TTS_ENABLED``
is true and both the ONNX file and its JSON config are present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

VOICE_BASE = "https://huggingface.co/ruslanmv/hp-piper-voices/resolve/main"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and _sha256(destination) == expected_sha256:
        print(f"already present: {destination}")
        return
    if destination.is_file():
        destination.unlink()
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - explicit model URL
        destination.write_bytes(response.read())
    if _sha256(destination) != expected_sha256:
        destination.unlink()
        raise RuntimeError(f"checksum mismatch for {destination.name}")


def _registry_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [Path.cwd() / "model_registry" / "voices.json"]
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / "model_registry" / "voices.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("model_registry/voices.json was not found")


def install_voices(cache_dir: Path) -> None:
    payload = json.loads(_registry_path().read_text(encoding="utf-8"))
    base = str((payload.get("source") or {}).get("base_url") or VOICE_BASE).rstrip("/")
    voice_dir = cache_dir / "tts"
    voice_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for item in payload.get("voices") or []:
        model_path = str(item.get("model_path") or "")
        config_path = str(item.get("config_path") or "")
        if not model_path or model_path in seen:
            continue
        seen.add(model_path)
        _download(f"{base}/{model_path}", voice_dir / Path(model_path).name, str(item.get("model_sha256") or ""))
        _download(f"{base}/{config_path}", voice_dir / Path(config_path).name, str(item.get("config_sha256") or ""))
        print(f"voice ready: {Path(model_path).stem}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install SonicAgent speech models")
    parser.add_argument("--model", default="tiny", help="Multilingual Whisper size. tiny.en is rejected.")
    parser.add_argument("--cache-dir", default="~/.cache/sonicagent-rt")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--tts", action="store_true", help="Also download every Piper voice in the registry")
    args = parser.parse_args(argv)
    cache = Path(args.cache_dir).expanduser()
    from sonicagent_rt.stt.model_store import install_whisper_model

    try:
        path = install_whisper_model(args.model, cache, revision=args.revision)
    except Exception as exc:
        print(f"model install failed: {exc}", file=sys.stderr)
        return 1
    print(f"whisper model ready: {path}")
    if args.tts:
        install_voices(cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
