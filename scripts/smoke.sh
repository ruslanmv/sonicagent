#!/usr/bin/env bash
set -euo pipefail
python -c "from sonicagent_rt.app import app; print(app.title)"
