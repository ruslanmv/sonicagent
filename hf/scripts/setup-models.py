"""Download the pinned multilingual Whisper checkpoint into the model cache.

Optional Piper voices are downloaded only with ``--tts``. They are not loaded
unless ``SONIC_TTS_ENABLED=true`` and both the ONNX file and its JSON config
are present.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

VOICE_FILES = {
    "en_US-lessac-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    ),
    "it_IT-paola-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json",
    ),
}


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 0:
        print(f"already present: {destination}")
        return
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - explicit model URL
        destination.write_bytes(response.read())


def install_voices(cache_dir: Path) -> None:
    voice_dir = cache_dir / "tts"
    voice_dir.mkdir(parents=True, exist_ok=True)
    for voice_id, (model_url, config_url) in VOICE_FILES.items():
        _download(model_url, voice_dir / f"{voice_id}.onnx")
        _download(config_url, voice_dir / f"{voice_id}.onnx.json")
        print(f"voice ready: {voice_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install SonicAgent speech models")
    parser.add_argument("--model", default="tiny", help="Multilingual Whisper size. tiny.en is rejected.")
    parser.add_argument("--cache-dir", default="~/.cache/sonicagent-rt")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--tts", action="store_true", help="Also download optional Piper en/it voices")
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
