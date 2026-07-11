from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def build_report(scenario: str, providers: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario": scenario,
        "providers": providers,
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurements": [
            {"metric": "first_audio_latency_ms", "p50": 0.0, "p95": 0.0, "p99": 0.0, "provider": providers}
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="benchmarks/scenarios/short_commands.yaml")
    parser.add_argument("--providers", default="fake")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(args.scenario, args.providers)
    payload = json.dumps(report, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n")
    print(payload)


if __name__ == "__main__":
    main()
