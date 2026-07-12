"""Report optional/runtime dependency availability without failing offline installs."""

from __future__ import annotations

import importlib.util

RUNTIME_MODULES = ("fastapi", "uvicorn", "pydantic", "httpx", "structlog", "prometheus_client")
DEV_MODULES = ("pytest", "ruff")


def missing_modules(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if importlib.util.find_spec(name) is None]


def main() -> int:
    missing_runtime = missing_modules(RUNTIME_MODULES)
    missing_dev = missing_modules(DEV_MODULES)
    if missing_runtime:
        print(
            "WARNING: offline install completed without runtime dependencies: " + ", ".join(missing_runtime)
        )
        print("Install project dependencies from an approved package mirror before running the API server.")
    if missing_dev:
        print("WARNING: missing development dependencies: " + ", ".join(missing_dev))
    if not missing_runtime and not missing_dev:
        print("Runtime and development dependency import checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
