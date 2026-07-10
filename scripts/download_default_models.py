from __future__ import annotations
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="~/.cache/sonicagent-rt")
    parser.add_argument("--minimal", action="store_true")
    args = parser.parse_args()
    cache = Path(args.cache_dir).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "README.txt").write_text(
        "SonicAgent-RT model cache. Real model downloads require registry checksum review.\n"
    )
    print(f"prepared model cache: {cache}")


if __name__ == "__main__":
    main()
