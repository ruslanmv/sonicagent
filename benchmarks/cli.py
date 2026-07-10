import argparse
import json
from datetime import datetime, timezone

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scaffold")
    args = parser.parse_args()
    print(json.dumps({"scenario": args.scenario, "status": "scaffold", "timestamp": datetime.now(timezone.utc).isoformat(), "measurements": []}, indent=2))

if __name__ == "__main__":
    main()
