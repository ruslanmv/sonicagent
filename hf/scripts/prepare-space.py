"""Stage a Hugging Face Space build context from this repository.

The staging directory contains only the files the voice image builds. It does
not include Git history, ``.env``, recordings, or dependency caches.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

EXCLUDED_PARTS = {
    ".git",
    ".env",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "node_modules",
    "recordings",
    "transcripts",
    "credentials.json",
    "id_rsa",
}
SKIP_SUFFIXES = {".pyc", ".onnx", ".wav", ".webm", ".mp3"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    def ignored(directory: str, names: list[str]) -> set[str]:
        blocked = set()
        for name in names:
            if name in EXCLUDED_PARTS or name.endswith(".egg-info") or Path(name).suffix in SKIP_SUFFIXES:
                blocked.add(name)
        return blocked

    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignored)


def stage(source: Path, destination: Path) -> list[str]:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    mapping = {
        source / "hf" / "Dockerfile": destination / "Dockerfile",
        source / "hf" / ".dockerignore": destination / ".dockerignore",
        source / "hf" / "README.space.md": destination / "README.md",
        source / "hf" / "app.py": destination / "hf" / "app.py",
        source / "hf" / "requirements.txt": destination / "hf" / "requirements.txt",
        source / "hf" / "scripts" / "setup-models.py": destination / "hf" / "scripts" / "setup-models.py",
        source / "pyproject.toml": destination / "pyproject.toml",
        source / "deploy" / "docker" / "healthcheck.py": destination / "deploy" / "docker" / "healthcheck.py",
    }
    written: list[str] = []
    for src, dest in mapping.items():
        if not src.is_file():
            raise FileNotFoundError(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        written.append(dest.relative_to(destination).as_posix())
    _copy_tree(source / "src", destination / "src")
    _copy_tree(source / "model_registry", destination / "model_registry")
    _copy_tree(source / "hf" / "ui", destination / "hf" / "ui")
    written.extend(["src", "model_registry", "hf/ui"])
    validate(destination)
    return written


def validate(destination: Path) -> None:
    dockerfile = (destination / "Dockerfile").read_text(encoding="utf-8")
    readme = (destination / "README.md").read_text(encoding="utf-8")
    engine = destination / "src" / "sonicagent_rt" / "stt" / "faster_whisper.py"
    if "7860" not in dockerfile:
        raise SystemExit("staged Dockerfile does not listen on port 7860")
    if "USER user" not in dockerfile:
        raise SystemExit("staged Dockerfile does not drop root")
    if "SONIC_API_KEY=" in dockerfile and "SONIC_API_KEY=\n" not in dockerfile:
        for line in dockerfile.splitlines():
            if line.strip().startswith("SONIC_API_KEY=") and line.strip() != "SONIC_API_KEY=":
                raise SystemExit("staged Dockerfile embeds an API key")
    if "sdk: docker" not in readme or "app_port: 7860" not in readme:
        raise SystemExit("staged Space README is missing Hugging Face metadata")
    text = engine.read_text(encoding="utf-8")
    if "WhisperModel" not in text:
        raise SystemExit("staged package does not include the Whisper engine")
    for name in ("index.html", "style.css", "app.js"):
        if not (destination / "hf" / "ui" / name).is_file():
            raise SystemExit(f"staged Space lacks frontend {name}")
    for path in destination.rglob("*"):
        if not path.is_file() and path.name in EXCLUDED_PARTS:
            raise SystemExit(f"staging contains excluded directory {path}")
        if path.name in {".env", "credentials.json"} or path.name.startswith(".env"):
            raise SystemExit(f"staging contains secret file {path}")
        if ".git" in path.parts:
            raise SystemExit("staging contains git metadata")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the Hugging Face Space build context")
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)
    source = args.source or repo_root()
    written = stage(source, args.dest)
    print(f"staged {len(written)} paths at {args.dest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"prepare-space failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
