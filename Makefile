.PHONY: install run test lint format typecheck test-contract test-integration web-install web-dev web-test docs-build smoke benchmark-smoke benchmark-endpoints models-min models-verify clean

install:
	python -m pip install --no-build-isolation --no-deps -e .
	python scripts/check_runtime_dependencies.py
	cd clients/web && npm ci

run:
	@echo "Starting SonicAgent-RT backend on :8000 and web demo on :5173"
	@(python -m sonicagent_rt --reload --host 0.0.0.0 --port 8000 & echo $$! > .sonicagent-backend.pid) ; \
	 cd clients/web && npm run dev -- --host 0.0.0.0

test:
	pytest tests/unit tests/contract
	cd clients/web && npm test -- --run

lint:
	ruff check src tests benchmarks scripts tools clients/python/src
	cd clients/web && npm run lint

format:
	ruff format src tests benchmarks scripts tools clients/python/src
	cd clients/web && npm run format -- --check

typecheck:
	mypy src/sonicagent_rt

test-contract:
	pytest tests/contract

test-integration:
	pytest tests/integration

web-install:
	cd clients/web && npm ci

web-dev:
	cd clients/web && npm run dev

web-test:
	cd clients/web && npm test -- --run

docs-build:
	mkdocs build --strict

smoke benchmark-smoke:
	python -m benchmarks.cli --scenario benchmarks/scenarios/short_commands.yaml --providers fake --output benchmarks/results/smoke.json

benchmark-endpoints:
	python -m benchmarks.endpoints.probe --base-url "$${SONIC_BENCH_URL:-https://ruslanmv-sonicagent.hf.space}" --repeats "$${SONIC_BENCH_REPEATS:-5}" --output benchmarks/results/endpoints.json --markdown benchmarks/results/endpoints.md

models-min:
	python scripts/download_default_models.py --cache-dir "$${SONIC_MODEL_CACHE_DIR:-$$HOME/.cache/sonicagent-rt}" --minimal

models-verify:
	python scripts/verify_model_checksums.py --registry model_registry

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build clients/web/dist benchmarks/results/smoke.json
