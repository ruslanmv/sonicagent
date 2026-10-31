#!/usr/bin/env bash
# Build the same voice image used by the Hugging Face Space.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
docker compose -f hf/docker-compose.yml build
