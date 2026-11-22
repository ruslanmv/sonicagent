"""The voice installer prefers mirrored files and verifies fallback downloads."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup-models.py"


@pytest.mark.parametrize("mirror_has_model", [True, False])
def test_install_voices_prefers_mirror_and_falls_back_on_missing_model(
    tmp_path, monkeypatch, mirror_has_model
):
    spec = importlib.util.spec_from_file_location("setup_models", SCRIPT)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    model = b"model bytes"
    config = b"config bytes"
    upstream_model = "https://upstream.example/revision/model.onnx"
    upstream_config = "https://upstream.example/revision/model.json"
    voice = {
        "model_path": "it/voice.onnx",
        "config_path": "it/voice.onnx.json",
        "model_sha256": hashlib.sha256(model).hexdigest(),
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "fallback_urls": [upstream_model, upstream_config],
    }
    registry = tmp_path / "voices.json"
    registry.write_text(json.dumps({"voices": [voice, voice]}), encoding="utf-8")
    monkeypatch.setattr(installer, "_registry_path", lambda: registry)
    mirror_model = f"{installer.VOICE_BASE}/it/voice.onnx"
    mirror_config = f"{installer.VOICE_BASE}/it/voice.onnx.json"
    requested = []

    def urlopen(url, *, timeout):
        requested.append(url)
        if url == mirror_model and not mirror_has_model:
            raise HTTPError(url, 404, "missing", {}, None)
        return io.BytesIO({mirror_model: model, upstream_model: model, mirror_config: config}[url])

    monkeypatch.setattr(installer.urllib.request, "urlopen", urlopen)
    installer.install_voices(tmp_path)
    installer.install_voices(tmp_path)
    expected = [mirror_model, mirror_config] if mirror_has_model else [mirror_model, upstream_model, mirror_config]
    assert requested == expected
    assert (tmp_path / "tts" / "voice.onnx").read_bytes() == model
    assert (tmp_path / "tts" / "voice.onnx.json").read_bytes() == config
