# Universal NVIDIA NIM Gateway

[![CI](https://github.com/iv150320/nvidia-nim-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/iv150320/nvidia-nim-gateway/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A single, universal OpenAI-compatible gateway for NVIDIA NIM inference
endpoints.** Route requests across multiple NIM providers with load balancing,
circuit breaker protection, automatic fallback, rate limiting, and full
observability — all behind a familiar OpenAI SDK interface.

---

## Features ✨

| Feature | Description |
|---------|-------------|
| **OpenAI-compatible API** | Chat Completions, Completions, Embeddings — drop-in replacement |
| **Load Balancing** | Weighted round-robin across equivalent NIM providers |
| **Circuit Breaker** | Per-provider failure detection (CLOSED → OPEN → HALF_OPEN) |
| **Model Fallback** | Automatic failover across ordered provider chains |
| **Caching** | In-memory TTL-based response cache (non-streaming) |
| **Rate Limiting** | Sliding-window per-client rate limiter |
| **Authentication** | Bearer token API key validation |
| **Prometheus Metrics** | Request counts, durations, provider stats |
| **OpenTelemetry** | Distributed tracing via OTLP HTTP |
| **Health Checks** | Periodic upstream provider health monitoring |
| **YAML Config** | Declarative provider and model routing configuration |
| **Docker Ready** | Multi-stage Docker image + docker-compose with monitoring stack |

## Quick Start 🚀

```bash
# Install
git clone https://github.com/iv150320/nvidia-nim-gateway.git
cd nvidia-nim-gateway

# Set up
cp .env.example .env
# Edit .env → set your NVIDIA_NIM_API_KEY

# Install dependencies
make install

# Run
make dev
```

Gateway starts at **http://localhost:8000**.
API docs at **http://localhost:8000/docs**.

### Test it

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Architecture 🏗️

```
┌──────────────┐     ┌──────────────────────────────────────────┐     ┌─────────────┐
│   Client     │────▶│         NVIDIA NIM Gateway                │────▶│  NIM API    │
│ (OpenAI SDK) │     │  ┌─────┐ ┌──────┐ ┌────────┐ ┌────────┐ │     │  (Primary)  │
└──────────────┘     │  │Auth │ │Cache │ │Router  │ │Metrics │ │     └─────────────┘
                     │  ├─────┤ ├──────┤ ├────────┤ ├────────┤ │            │
                     │  │Rate │ │CB    │ │Fallback│ │OTEL    │ │     ┌─────▼──────┐
                     │  │Lmt  │ │      │ │Chain   │ │        │ │     │  NIM API   │
                     │  └─────┘ └──────┘ └────────┘ └────────┘ │     │  (Fallback)│
                     └──────────────────────────────────────────┘     └─────────────┘
```

## Configuration 🔧

Define providers and route mapping in `config/models.yaml`:

```yaml
providers:
  nim-primary:
    base_url: "https://integrate.api.nvidia.com"
    api_key: "${NVIDIA_NIM_API_KEY}"
    weight: 3
    timeout: 120.0

routes:
  "meta/llama-3.1-405b-instruct":
    providers: ["nim-primary", "nim-fallback"]
    max_tokens: 16384
```

Gateway settings in `config/gateway.yaml`.

## Deployment 🐳

```bash
# Build & start
make docker-build
make docker-up

# Full stack with Prometheus + Grafana + OpenTelemetry
make docker-up-all

# Docker Compose directly
docker compose -f docker/docker-compose.yml --profile monitoring --profile cache up -d
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `install` | Install Python deps |
| `dev` | Dev server with hot-reload |
| `test` | Run test suite |
| `lint` | Code linting |
| `format` | Auto-format code |
| `docker-build` | Build Docker image |
| `docker-up` | Start gateway |
| `docker-up-all` | Start full stack |
| `gen-key` | Generate API key |

## Roadmap 🗺️

See [ROADMAP.md](ROADMAP.md) for planned features:

- **ft2** — Redis-backed rate limiting & caching, load testing
- **ft3** — Grafana dashboards, JSON logging, alerting
- **ft4** — Admin API, tools/function calling, vision support
- **ft5** — RBAC, SSO, multi-tenant, Kubernetes Helm chart

## Changelog 📝

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License 📄

MIT — see [LICENSE](LICENSE).
