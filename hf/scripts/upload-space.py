"""Upload a prepared Space directory through the Hub API.

The Space rejects a Git upload of this tree because it contains audio files.
The Hub client stores those files in Xet storage and commits the rest as text.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _local_files(dest: Path) -> set[str]:
    return {path.relative_to(dest).as_posix() for path in dest.rglob("*") if path.is_file()}


def stale_remote_paths(local: set[str], remote: set[str]) -> list[str]:
    """Remote paths that are not in the staged tree.

    ``.gitattributes`` stays. Xet uses it to address the audio files, and the
    Hub client also refuses to delete that file.
    """
    return sorted(path for path in remote if path not in local and path != ".gitattributes")


def upload_space(dest: Path, *, repo_id: str, token: str, message: str) -> int:
    from huggingface_hub import HfApi

    try:
        import hf_xet  # noqa: F401
    except ImportError:
        print("hf_xet is required so audio files upload through Xet storage.", file=sys.stderr)
        return 1
    if not dest.is_dir():
        print(f"deploy directory does not exist: {dest}", file=sys.stderr)
        return 1
    api = HfApi(token=token)
    local = _local_files(dest)
    if not local:
        print("deploy directory is empty", file=sys.stderr)
        return 1
    remote = set(api.list_repo_files(repo_id=repo_id, repo_type="space"))
    stale = stale_remote_paths(local, remote)
    api.upload_folder(
        folder_path=str(dest),
        repo_id=repo_id,
        repo_type="space",
        commit_message=message,
        delete_patterns=stale or None,
    )
    print(f"uploaded {len(local)} files to {repo_id}; removed {len(stale)} stale files")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload a prepared Hugging Face Space tree")
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)
    username = os.environ.get("HF_USERNAME", "").strip()
    space = os.environ.get("SPACE_NAME", "").strip()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not username or not space:
        print("Missing HF_USERNAME or SPACE_NAME.", file=sys.stderr)
        return 1
    if not token:
        print("Missing HF_TOKEN.", file=sys.stderr)
        return 1
    sha = os.environ.get("GITHUB_SHA", "manual")
    return upload_space(
        args.dest,
        repo_id=f"{username}/{space}",
        token=token,
        message=f"Deploy from {sha}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
