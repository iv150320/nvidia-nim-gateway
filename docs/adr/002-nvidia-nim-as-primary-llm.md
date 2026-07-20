# ADR-002: NVIDIA NIM as Primary LLM Provider

## Status
Accepted

## Context
The project requires LLM inference. Multiple providers exist (OpenAI, Anthropic, Google, local models via Ollama/vLLM).

## Decision
NVIDIA NIM is the sole LLM provider:

- OpenAI-compatible API (standard chat completions, embeddings)
- Access via `integrate.api.nvidia.com` or self-hosted NIM microservices
- All LLM calls go through a client abstraction (NIMClient) for testability
- Mock fallback when API key is absent (development mode)

## Consequences
- Single dependency simplifies architecture
- Self-hosted NIM option available for air-gapped deployments
- OpenAI-compatible API allows future provider swaps via the adapter pattern

## Compliance
All LLM access must go through `app/infrastructure/nvidia_nim/client.py` or equivalent.
