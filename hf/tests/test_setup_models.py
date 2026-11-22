"""The voice installer takes every voice from the mirror, checksum-pinned, and reuses its cache.

`ruslanmv/hp-piper-voices` is the one source of truth for voice files: a voice joins the
registry only once its exact bytes are on the mirror (Aurora and Giorgio were uploaded there,
byte for byte from Piper Italiano, before this became the rule for them too).
"""

import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "hf" / "scripts" / "setup-models.py"


def _installer():
    spec = importlib.util.spec_from_file_location("setup_models", SCRIPT)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    return installer


def _registry(tmp_path, voice):
    registry = tmp_path / "voices.json"
    registry.write_text(json.dumps({"voices": [voice, voice]}), encoding="utf-8")
    return registry


def test_install_voices_downloads_from_the_mirror_once_and_reuses_the_cache(tmp_path, monkeypatch):
    installer = _installer()
    model, config = b"model bytes", b"config bytes"
    voice = {
        "model_path": "it/voice.onnx",
        "config_path": "it/voice.onnx.json",
        "model_sha256": hashlib.sha256(model).hexdigest(),
        "config_sha256": hashlib.sha256(config).hexdigest(),
    }
    monkeypatch.setattr(installer, "_registry_path", lambda: _registry(tmp_path, voice))
    mirror = {
        f"{installer.VOICE_BASE}/it/voice.onnx": model,
        f"{installer.VOICE_BASE}/it/voice.onnx.json": config,
    }
    requested = []

    def urlopen(url, *, timeout):
        requested.append(url)
        return io.BytesIO(mirror[url])

    monkeypatch.setattr(installer.urllib.request, "urlopen", urlopen)
    installer.install_voices(tmp_path)
    installer.install_voices(tmp_path)  # second run: cached and verified, nothing fetched
    assert requested == list(mirror)
    assert (tmp_path / "tts" / "voice.onnx").read_bytes() == model
    assert (tmp_path / "tts" / "voice.onnx.json").read_bytes() == config


def test_bytes_that_do_not_match_the_pinned_checksum_are_refused(tmp_path, monkeypatch):
    installer = _installer()
    voice = {
        "model_path": "it/voice.onnx",
        "config_path": "it/voice.onnx.json",
        "model_sha256": hashlib.sha256(b"expected").hexdigest(),
        "config_sha256": hashlib.sha256(b"config").hexdigest(),
    }
    monkeypatch.setattr(installer, "_registry_path", lambda: _registry(tmp_path, voice))
    monkeypatch.setattr(installer.urllib.request, "urlopen", lambda url, *, timeout: io.BytesIO(b"tampered"))
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        installer.install_voices(tmp_path)
    assert not (tmp_path / "tts" / "voice.onnx").exists()


def test_every_registry_voice_comes_from_the_mirror_only() -> None:
    payload = json.loads((ROOT / "model_registry" / "voices.json").read_text(encoding="utf-8"))
    assert (
        payload["source"]["base_url"].rstrip("/")
        == "https://huggingface.co/ruslanmv/hp-piper-voices/resolve/main"
    )
    for voice in payload["voices"]:
        assert "fallback_urls" not in voice, voice["id"]
        assert not voice["model_path"].startswith(("http:", "https:")), voice["id"]
        assert not voice["config_path"].startswith(("http:", "https:")), voice["id"]
