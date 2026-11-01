#!/usr/bin/env bash
# Run SonicAgent locally on port 8000 (container port 7860).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ -f hf/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source hf/.env
  set +a
fi
if [[ -z "${SONIC_API_KEY:-}" || "${#SONIC_API_KEY}" -lt 16 ]]; then
  echo "Set SONIC_API_KEY in the environment or hf/.env (at least 16 characters)." >&2
  exit 1
fi
docker compose -f hf/docker-compose.yml up --build
