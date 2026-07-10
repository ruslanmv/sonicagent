#!/usr/bin/env bash
set -euo pipefail
exec uvicorn sonicagent_rt.app:app --reload --host 0.0.0.0 --port 8000
