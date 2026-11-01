"""Install a local CTranslate2 Whisper checkpoint.

The download step is explicit. Request handling never calls this module.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sonicagent_rt.stt.models import PINNED_MODEL_SHA256, PINNED_REVISIONS, WHISPER_REPOS, canonical_size, public_model_id


def manifest_path(model_dir: Path) -> Path:
    return model_dir / "model.manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(model_dir: Path, size: str) -> dict[str, str]:
    model_bin = model_dir / "model.bin"
    payload = {
        "id": public_model_id(size),
        "size": size,
        "repo": WHISPER_REPOS.get(size, ""),
        "revision": PINNED_REVISIONS.get(size, ""),
        "model_bin_sha256": sha256_file(model_bin),
        "license": "MIT",
    }
    manifest_path(model_dir).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    expected = PINNED_MODEL_SHA256.get(size)
    if expected and payload["model_bin_sha256"] != expected:
        raise RuntimeError("downloaded speech model checksum does not match the pinned tiny checkpoint")
    return payload


def verify_manifest(model_dir: Path) -> None:
    """Refuse to load a directory whose manifest disagrees with ``model.bin``."""
    path = manifest_path(model_dir)
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("speech model manifest is unreadable") from exc
    expected = str(data.get("model_bin_sha256") or "")
    if len(expected) != 64:
        raise RuntimeError("speech model manifest is missing a checksum")
    actual = sha256_file(model_dir / "model.bin")
    if actual != expected:
        raise RuntimeError("speech model checksum does not match its manifest")


def install_whisper_model(size: str, cache_dir: Path, *, revision: str | None = None) -> Path:
    """Download ``size`` into ``cache_dir/stt/<size>`` when it is not already present."""
    canonical = canonical_size(size)
    destination = Path(cache_dir).expanduser() / "stt" / canonical
    destination.mkdir(parents=True, exist_ok=True)
    model_bin = destination / "model.bin"
    if model_bin.is_file() and (destination / "tokenizer.json").is_file():
        if not manifest_path(destination).is_file():
            write_manifest(destination, canonical)
        else:
            verify_manifest(destination)
        return destination
    try:
        from faster_whisper.utils import download_model
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed") from exc
    pinned = revision if revision is not None else PINNED_REVISIONS.get(canonical)
    download_model(canonical, output_dir=str(destination), revision=pinned or None)
    if not model_bin.is_file():
        raise RuntimeError("speech model download did not produce model.bin")
    write_manifest(destination, canonical)
    return destination
