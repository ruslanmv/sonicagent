#!/usr/bin/env bash
# Prepare, and optionally upload, the existing Space ruslanmv/SonicAgent.
# Authentication must already be available to the Hugging Face CLI.
# This script never reads or prints an access token.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PUSH=0
if [[ "${1:-}" == "--push" ]]; then
  PUSH=1
fi
STAGE="$(mktemp -d)"
python3 "$ROOT/hf/scripts/prepare-space.py" --dest "$STAGE"
echo "Staging validated at $STAGE"
echo "Managed paths:"
find "$STAGE" -type f | sed "s|$STAGE/||" | sort
if [[ "$PUSH" -eq 0 ]]; then
  echo
  echo "Dry run. Nothing was uploaded."
  echo "After hf auth login, publish with:"
  echo "  hf/scripts/deploy-space.sh --push"
  echo "Or manually:"
  echo "  hf upload ruslanmv/SonicAgent \"$STAGE\" . --repo-type=space --commit-message \"Deploy SonicAgent voice service\""
  exit 0
fi
if ! command -v hf >/dev/null 2>&1; then
  echo "The hf CLI is not on PATH. Install it and run hf auth login, then retry." >&2
  echo "Staging left at $STAGE" >&2
  exit 1
fi
if ! hf auth whoami >/dev/null 2>&1; then
  echo "Hugging Face CLI is not authenticated. Run hf auth login and retry." >&2
  echo "Staging left at $STAGE" >&2
  exit 1
fi
hf upload ruslanmv/SonicAgent "$STAGE" . --repo-type=space \
  --commit-message "Deploy SonicAgent voice service"
echo "Upload submitted for https://huggingface.co/spaces/ruslanmv/SonicAgent"
rm -rf "$STAGE"
