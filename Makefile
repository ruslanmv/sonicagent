.PHONY: bootstrap dev test lint format typecheck test-contract test-integration web-install web-dev web-test benchmark-smoke models-min clean

bootstrap:
	python -m pip install -e '.[dev]'
	@if command -v npm >/dev/null 2>&1; then cd clients/web && npm install; else echo "npm not found; skipping web dependencies"; fi

dev:
	uvicorn sonicagent_rt.app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/unit tests/contract

lint:
	ruff check src tests benchmarks scripts tools clients/python/src

format:
	ruff format src tests benchmarks scripts tools clients/python/src

typecheck:
	mypy src/sonicagent_rt

test-contract:
	pytest tests/contract

test-integration:
	pytest tests/integration

web-install:
	cd clients/web && npm install

web-dev:
	cd clients/web && npm run dev

web-test:
	cd clients/web && npm test

benchmark-smoke:
	python -m benchmarks.cli --scenario scaffold

models-min:
	@echo "Model downloads are disabled in the scaffold. Review registry hashes and implement scripts first."

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build clients/web/dist
