"""Add registry voices to the `ruslanmv/hp-piper-voices` mirror: additive only, checksum-checked.

The mirror is the one source of truth for voice files (`hf/tests/test_setup_models.py`), so a new
voice goes there BEFORE its registry entry is merged. This does what was done by hand for Aurora
and Giorgio (mirror commit 7d75eff):

  1. each voice's model and config are taken from a local directory and must match the SHA-256
     pinned in `model_registry/voices.json`;
  2. every target path must be ABSENT on the mirror: nothing is overwritten or deleted;
  3. a non-MIT voice gets a `MODEL_CARD` beside its files (the mirror's convention, as for Serena
     and Daniela), written from the registry entry and the voice's own config;
  4. one commit, pinned to the mirror's current head (`parent_commit`), so a concurrent change
     makes it fail instead of racing.

Dry run by default. The token is read from HF_TOKEN and never printed.

    HF_TOKEN=... python hf/scripts/mirror-add-voices.py --files /tmp/sa-cache/tts it_IT-aurora-medium
    HF_TOKEN=... python hf/scripts/mirror-add-voices.py --files /tmp/sa-cache/tts it_IT-aurora-medium --push

The mirror's README.md (voice count, per-language rows, licence table) is NOT touched here: that
edit changes an existing file, so it is a separate, reviewed commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "ruslanmv/hp-piper-voices"


def model_card(entry: dict, config: dict) -> str:
    audio = config.get("audio") or {}
    rate = audio.get("sample_rate")
    lang = entry["locale"].replace("-", "_")
    lines = [
        f"# Model card for {entry['id'].split('-')[1]} ({entry['quality']})",
        "",
        f"* Language: {lang} ({entry.get('language_label', entry['language'])})",
        f"* Speakers: {config.get('num_speakers', 1)}",
        f"* Quality: {entry['quality']}",
        f"* Samplerate: {rate:,}Hz" if rate else "* Samplerate: see config",
        "",
        "## Source and credit",
        "",
        f"* {entry['attribution']}",
        f"* License: {entry['license']}",
        f"* Source project: {entry.get('source_project', 'unknown')}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--files", required=True, type=Path, help="directory holding <voice>.onnx and .onnx.json")
    ap.add_argument("--push", action="store_true", help="make the commit (default: dry run)")
    ap.add_argument("voices", nargs="+")
    a = ap.parse_args()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("HF_TOKEN is not set", file=sys.stderr)
        return 1
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi(token=token)
    head = api.model_info(REPO).sha
    existing = set(api.list_repo_files(REPO, revision=head))
    registry = {
        v["id"]: v for v in json.loads((ROOT / "model_registry" / "voices.json").read_text("utf-8"))["voices"]
    }
    ops, problems = [], []
    for vid in a.voices:
        entry = registry.get(vid)
        if entry is None:
            problems.append(f"{vid}: not in model_registry/voices.json")
            continue
        for key, sha_key in (("model_path", "model_sha256"), ("config_path", "config_sha256")):
            rel = entry[key]
            local = a.files / Path(rel).name
            if rel in existing:
                problems.append(f"{rel}: already on the mirror (this script never overwrites)")
            elif not local.is_file():
                problems.append(f"{local}: missing")
            elif hashlib.sha256(local.read_bytes()).hexdigest() != entry[sha_key]:
                problems.append(f"{local}: SHA-256 does not match the registry")
            else:
                ops.append(CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(local)))
        if entry["license"] != "MIT":
            card_path = str(Path(entry["model_path"]).parent / "MODEL_CARD")
            config_file = a.files / Path(entry["config_path"]).name
            if card_path in existing:
                problems.append(f"{card_path}: already on the mirror")
            elif not entry.get("attribution"):
                problems.append(f"{vid}: non-MIT voice without an attribution in the registry")
            elif config_file.is_file():
                card = model_card(entry, json.loads(config_file.read_text("utf-8")))
                ops.append(CommitOperationAdd(path_in_repo=card_path, path_or_fileobj=card.encode()))
                print(f"--- {card_path}\n{card}")
    print(f"mirror head {head}; {len(ops)} files to add")
    for op in ops:
        print("  +", op.path_in_repo)
    if problems:
        print("refusing:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    if not a.push:
        print("dry run: nothing uploaded (add --push)")
        return 0
    commit = api.create_commit(
        REPO,
        operations=ops,
        parent_commit=head,
        commit_message="Add " + ", ".join(a.voices),
        commit_description="Additive: new files only. Bytes match the SHA-256 pinned in SonicAgent's "
        "model_registry/voices.json.",
    )
    after = set(api.list_repo_files(REPO))
    assert existing <= after, "a file disappeared from the mirror"
    print("commit", commit.oid, "| added", len(after - existing), "| removed", len(existing - after))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
