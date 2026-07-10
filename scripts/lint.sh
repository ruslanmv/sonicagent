#!/usr/bin/env bash
set -euo pipefail
ruff check src tests benchmarks scripts tools clients/python/src
