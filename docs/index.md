# Universal NVIDIA NIM Gateway

Welcome to the **Universal NVIDIA NIM Gateway** documentation.

## Quick Start

```bash
# Install dependencies
make install

# Run in development mode
make dev

# Run tests
make test
```

## Architecture

```
┌──────────────┐     ┌──────────────────────────────┐     ┌─────────────┐
│   Client     │────▶│   NVIDIA NIM Gateway          │────▶│  NIM API    │
│ (OpenAI SDK) │     │  ┌─────┐ ┌──────┐ ┌────────┐ │     │  (Primary)  │
└──────────────┘     │  │Auth │ │Cache │ │Router  │ │     └─────────────┘
                     │  ├─────┤ ├──────┤ ├────────┤ │            │
                     │  │Rate │ │Metrics│ │Fallback│ │     ┌─────▼──────┐
                     │  │Lmt  │ │CB    │ │Chain   │ │     │  NIM API   │
                     │  └─────┘ └──────┘ └────────┘ │     │  (Fallback)│
                     └──────────────────────────────┘     └─────────────┘
```

## Configuration

Edit `config/models.yaml` to define your NVIDIA NIM providers and route
public model names to provider chains:

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
    rpm_limit: 60
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | Chat Completions (streaming + non-streaming) |
| POST | `/v1/completions` | Text Completions |
| POST | `/v1/embeddings` | Embeddings |
| GET | `/v1/models` | List models |
| GET | `/v1/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

## Deployment

```bash
# Docker Compose (gateway only)
make docker-up

# Full stack with monitoring
make docker-up-all
```
