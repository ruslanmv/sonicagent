#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e ".[dev]"
if command -v npm >/dev/null 2>&1; then (cd clients/web && npm install); fi
