# ROADMAP

## 🚀 ft1 — Initial Release (Current)
- [x] OpenAI-compatible API endpoints (chat, completions, embeddings)
- [x] Load balancing across multiple NIM providers
- [x] Circuit breaker pattern (per-provider)
- [x] Model fallback chain
- [x] API key authentication
- [x] In-memory rate limiting
- [x] In-memory response caching
- [x] Structured request logging
- [x] Prometheus metrics
- [x] OpenTelemetry integration (OTLP HTTP)
- [x] Provider health checks
- [x] YAML-driven configuration
- [x] Docker deployment (gateway + monitoring stack)
- [x] CI pipeline (lint, test, build)

## 📋 ft2 — Production Hardening
- [ ] Redis-backed rate limiting (token bucket)
- [ ] Redis-backed distributed caching
- [ ] Concurrent request limiting (semaphore per provider)
- [ ] Request timeouts per model (configurable)
- [ ] Response streaming via Server-Sent Events (robust error handling)
- [ ] Connection pooling tuning
- [ ] Graceful shutdown with in-flight request draining
- [ ] Comprehensive test suite (>80% coverage)
- [ ] Load testing framework (locust/k6)
- [ ] Performance benchmarking report

## 📋 ft3 — Observability & Operations
- [ ] Grafana dashboard (pre-built JSON)
- [ ] Structured log format (JSON)
- [ ] Log aggregation config (Loki / ELK sidecar)
- [ ] Distributed tracing spans for each hop
- [ ] Provider-level latency percentiles
- [ ] Alert rules (Prometheus + Alertmanager)
- [ ] API usage analytics (per-key, per-model)
- [ ] Cost tracking (token counters per provider)

## 📋 ft4 — Advanced Features
- [ ] API key management API (CRUD for keys)
- [ ] Provider configuration API (hot-reload without restart)
- [ ] Admin dashboard (web UI)
- [ ] Multi-region routing (latency-based)
- [ ] Request queuing (for burst handling)
- [ ] Response streaming to S3 (for large outputs)
- [ ] Webhook callbacks for async completions
- [ ] Tool/function calling support (native NVIDIA NIM)
- [ ] Vision model support (image inputs)

## 📋 ft5 — Enterprise
- [ ] RBAC (role-based access control)
- [ ] Audit logging (immutable event stream)
- [ ] SSO / OIDC integration
- [ ] Usage billing (per-token metering)
- [ ] SLA monitoring
- [ ] Multi-tenant isolation
- [ ] Compliance reports
- [ ] Blue-green deployment strategy
- [ ] Kubernetes Helm chart
- [ ] Terraform modules for cloud deployment
