# Prepare or upload the existing Hugging Face Space ruslanmv/SonicAgent.
# Pass -Push only after `hf auth login`. This script never asks for a token.
param(
    [switch]$Push
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ("sonicagent-space-" + [guid]::NewGuid().ToString("N"))
python "$Root/hf/scripts/prepare-space.py" --dest $Stage
Write-Host "Staging validated at $Stage"
if (-not $Push) {
    Write-Host "Dry run. Nothing was uploaded."
    Write-Host "After hf auth login, publish with: ./hf/scripts/deploy-space.ps1 -Push"
    exit 0
}
if (-not (Get-Command hf -ErrorAction SilentlyContinue)) {
    Write-Error "The hf CLI is not on PATH. Install it, run hf auth login, and retry. Staging left at $Stage"
}
hf auth whoami | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Hugging Face CLI is not authenticated. Run hf auth login. Staging left at $Stage"
}
hf upload ruslanmv/SonicAgent $Stage . --repo-type=space --commit-message "Deploy SonicAgent voice service"
Write-Host "Upload submitted for https://huggingface.co/spaces/ruslanmv/SonicAgent"
Remove-Item -Recurse -Force $Stage
