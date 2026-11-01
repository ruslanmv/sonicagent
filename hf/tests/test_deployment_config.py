"""Static checks for the Hugging Face and local Docker package."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HF = ROOT / "hf"


def test_required_files_exist() -> None:
    required = [
        "README.md",
        "README.space.md",
        "Dockerfile",
        ".dockerignore",
        "requirements.txt",
        "app.py",
        ".env.example",
        "docker-compose.yml",
        "scripts/build-local.sh",
        "scripts/run-local.sh",
        "scripts/run-local.ps1",
        "scripts/setup-models.py",
        "scripts/smoke-test.py",
        "scripts/prepare-space.py",
        "scripts/deploy-space.sh",
        "scripts/deploy-space.ps1",
        "scripts/upload-space.py",
    ]
    missing = [name for name in required if not (HF / name).is_file()]
    assert missing == []


def test_dockerfile_is_non_root_python311_on_7860() -> None:
    text = (HF / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.11" in text
    assert "USER user" in text
    assert "EXPOSE 7860" in text
    assert '--port", "7860"' in text
    assert "7860" in text
    assert "SONIC_API_KEY=" not in text
    assert "faster-whisper" in (HF / "requirements.txt").read_text(encoding="utf-8")
    compose = (HF / "docker-compose.yml").read_text(encoding="utf-8")
    assert "8000:7860" in compose or "${SONIC_PUBLISH_PORT:-8000}:7860" in compose
    assert "context: .." in compose


def test_space_readme_metadata() -> None:
    text = (HF / "README.space.md").read_text(encoding="utf-8")
    assert "sdk: docker" in text
    assert "app_port: 7860" in text
    assert "title: SonicAgent" in text


def test_powershell_scripts_are_balanced_and_do_not_embed_secrets() -> None:
    for name in ("run-local.ps1", "deploy-space.ps1"):
        text = (HF / "scripts" / name).read_text(encoding="utf-8")
        assert text.count("{") == text.count("}")
        assert "hf_" not in text
        assert "BEGIN OPENSSH PRIVATE KEY" not in text
        assert "SONIC_API_KEY=" not in text or "SONIC_API_KEY" in text


def test_staging_contains_engine_and_no_secrets(tmp_path: Path) -> None:
    destination = tmp_path / "space"
    subprocess.run(
        [sys.executable, str(HF / "scripts" / "prepare-space.py"), "--dest", str(destination)],
        check=True,
        cwd=ROOT,
    )
    engine = destination / "src" / "sonicagent_rt" / "stt" / "faster_whisper.py"
    assert "WhisperModel" in engine.read_text(encoding="utf-8")
    dockerfile = (destination / "Dockerfile").read_text(encoding="utf-8")
    assert "7860" in dockerfile
    assert "USER user" in dockerfile
    assert not (destination / ".git").exists()
    assert not (destination / ".env").exists()
    assert (destination / "README.md").read_text(encoding="utf-8").startswith("---")
    secret_names = [path.name for path in destination.rglob("*") if path.name == ".env" or path.name == "credentials.json"]
    assert secret_names == []
    examples = {path.name for path in (destination / "hf" / "ui" / "examples").glob("*.wav")}
    assert {
        "en_GB-cori-medium.wav",
        "en_US-kristin-medium.wav",
        "es_MX-ald-companion.wav",
        "es_MX-ald-medium.wav",
        "fr_FR-upmc-medium.wav",
    } <= examples


def test_master_push_deploys_the_prepared_space() -> None:
    text = (ROOT / ".github" / "workflows" / "huggingface-space.yml").read_text(encoding="utf-8")
    assert 'branches: ["main", "master"]' in text
    assert "hf/scripts/prepare-space.py" in text
    assert "hf/scripts/upload-space.py" in text
    assert "hf-xet" in text
    assert "secrets.HF_TOKEN" in text
    assert "secrets.HF_USERNAME" in text
    assert "secrets.SPACE_NAME" in text
    assert "git push" not in text
    assert "https://${HF_USERNAME}:${HF_TOKEN}" not in text
    script = (HF / "scripts" / "upload-space.py").read_text(encoding="utf-8")
    assert "upload_folder" in script
    assert "hf_xet" in script
    assert "git push" not in script
    assert "subprocess" not in script
    assert "HF_TOKEN" in script


def test_stale_remote_paths_keep_attributes_and_current_files() -> None:
    path = HF / "scripts" / "upload-space.py"
    spec = importlib.util.spec_from_file_location("upload_space", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stale = module.stale_remote_paths(
        {"Dockerfile", "hf/ui/examples/en_GB-cori-medium.wav"},
        {
            ".gitattributes",
            "Dockerfile",
            "old/readme.md",
            "hf/ui/examples/en_GB-cori-medium.wav",
        },
    )
    assert stale == ["old/readme.md"]


def test_shell_scripts_have_bash_syntax() -> None:
    for name in ("build-local.sh", "run-local.sh", "deploy-space.sh"):
        subprocess.run(["bash", "-n", str(HF / "scripts" / name)], check=True)
