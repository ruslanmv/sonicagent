#!/usr/bin/env bash
# Write a CycloneDX SBOM for the installed Python environment.
# This does not sign the file and it does not scan the container image.
set -euo pipefail
output="${1:-sbom.cdx.json}"
if ! python3 -m cyclonedx_py --help >/dev/null 2>&1; then
  echo "Install cyclonedx-bom in the environment you want to describe, then rerun." >&2
  exit 1
fi
python3 -m cyclonedx_py environment --output-format JSON --outfile "$output"
echo "Wrote $output"
