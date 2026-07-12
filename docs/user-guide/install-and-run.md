# Install and run

This page explains the safest local-development path. You do not need to be an
expert, but you should be comfortable opening a terminal.

## 1. Requirements

Install these first:

- Python 3.11 or newer.
- Node.js 20 or newer.
- npm, which normally comes with Node.js.
- Access to your approved Python package mirror if you want to run the backend.

## 2. Get the code

```bash
git clone https://github.com/your-org/sonicagent-rt.git
cd sonicagent-rt
```

If you already have the repository, open a terminal in the repository root.

## 3. Install local dependencies

```bash
make install
```

This installs the local Python package and the web client dependencies.
In restricted/offline environments, the command may warn that runtime modules
such as `fastapi` or `uvicorn` are missing. That warning means tests may still
run, but the backend server cannot start until those modules are installed.

## 4. Check the package

```bash
python -m sonicagent_rt --help
python -c "import sonicagent_rt; print(sonicagent_rt.__version__)"
```

The first command should print command-line help. The second command should print
the package version.

## 5. Run tests

```bash
make test
```

A passing test command means the deterministic test suite completed. If pytest
reports skipped scaffold tests, the project is still not production-ready.

## 6. Run the fake-provider smoke check

```bash
make smoke
```

This uses deterministic fake providers. It does not prove real model performance.

## 7. Start the local app

```bash
make run
```

Expected local URLs:

| Service | URL |
| --- | --- |
| Backend API | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| Live health | `http://localhost:8000/health/live` |
| Browser demo | `http://localhost:5173` |

If the backend prints `uvicorn is not installed`, install runtime dependencies
from your approved package mirror, then run `make run` again.

## Stop the app

Press `Ctrl+C` in the terminal running `make run`.
