# Run SonicAgent on Windows Docker Desktop.
# The published address is http://localhost:8000 while the container listens on 7860.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root
if (-not $env:SONIC_API_KEY -or $env:SONIC_API_KEY.Length -lt 16) {
    Write-Error "Set SONIC_API_KEY to a private value of at least 16 characters before starting."
}
docker compose -f hf/docker-compose.yml up --build
