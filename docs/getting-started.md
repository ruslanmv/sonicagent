## Quick start: scaffold mode

### Requirements

- Python 3.11 or newer.
- Node.js 20 or newer for the browser client.
- `uv` recommended for Python dependency management.
- Docker and Docker Compose are optional.

### Local development

```bash
git clone https://github.com/your-org/SonicAgent.git
cd SonicAgent
cp .env.example .env
make bootstrap
make dev
```

The scaffold server exposes:

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health/live`
- Readiness: `http://localhost:8000/health/ready`
- Browser client: `http://localhost:5173`

The default provider profile uses a deterministic mock LLM and does not download or execute neural models.

### Docker Compose

```bash
docker compose up --build
```

The root Compose file starts the API and web scaffold. Real model volumes, GPU access, Redis, Prometheus, Grafana, and OpenTelemetry are provided as deployment templates under `deploy/`.

