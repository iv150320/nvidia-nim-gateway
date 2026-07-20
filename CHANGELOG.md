# Changelog

All notable changes to the **Universal NVIDIA NIM Gateway** are documented
here. This project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-07-20 — ft1 🚀

### Added
- **FastAPI application** with OpenAI-compatible endpoints:
  - `POST /v1/chat/completions` — Chat Completions (streaming + non-streaming)
  - `POST /v1/completions` — Text Completions
  - `POST /v1/embeddings` — Embeddings
  - `GET /v1/models` — List available models
  - `GET /v1/health` / `GET /health` — Health check
  - `GET /metrics` — Prometheus metrics
- **Gateway routing** — maps public model names to provider chains
- **Load balancing** — weighted round-robin across equivalent providers
- **Circuit breaker** — per-provider failure protection (CLOSED / OPEN / HALF_OPEN)
- **Model fallback** — automatic failover across ordered provider list
- **Authentication** — Bearer token API key validation
- **Rate limiting** — sliding-window per-client rate limiter
- **Response caching** — in-memory TTL-based cache (non-streaming only)
- **Structured logging** — per-request ID, method, path, status, duration
- **Prometheus metrics** — request counts, durations, provider stats
- **OpenTelemetry** — OTLP HTTP exporter for traces
- **Health checker** — periodic upstream provider health monitoring
- **YAML configuration** — `config/gateway.yaml` + `config/models.yaml`
- **Docker support** — Dockerfile + docker-compose with Prometheus, Grafana,
  Redis, and OpenTelemetry collector
- **CI pipeline** — GitHub Actions (lint, test, build)

### Infrastructure
- Python 3.12 / FastAPI / httpx / Pydantic v2
- Weighted load balancing with circuit breaker isolation
- Multi-stage Docker build for minimal image size
- Makefile shortcuts for common workflows
