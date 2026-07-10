#!/usr/bin/env bash
set -euo pipefail
ruff format src tests benchmarks scripts tools clients/python/src
