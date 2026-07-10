from __future__ import annotations
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="model_registry")
    args = parser.parse_args()
    root = Path(args.registry)
    for name in ("voices.json", "stt_models.json"):
        data = json.loads((root / name).read_text())
        assert isinstance(data, dict)
    print(f"registry metadata readable: {root}")


if __name__ == "__main__":
    main()
