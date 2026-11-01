import json
from pathlib import Path


def test_piper_voice_checksums_are_pinned() -> None:
    payload = json.loads(Path("model_registry/voices.json").read_text(encoding="utf-8"))
    voices = payload["voices"]
    assert len(voices) == 49
    for voice in voices:
        assert len(voice["model_sha256"]) == 64
        assert len(voice["config_sha256"]) == 64
        assert voice["model_sha256"] != "TODO"
        assert voice["config_sha256"] != "TODO"
        int(voice["model_sha256"], 16)
        int(voice["config_sha256"], 16)
