# ADR-003: Async-First Architecture

## Status
Accepted

## Context
AI workloads involve heavy I/O (HTTP calls to NIM, database queries, file operations). Synchronous code would waste resources blocking on I/O.

## Decision
The entire backend stack is async-first:

- FastAPI (ASGI) — async request handling
- SQLAlchemy 2.0 async sessions — non-blocking database access
- httpx.AsyncClient — non-blocking HTTP calls
- async Celery workers for background tasks

## Consequences
- Higher throughput under concurrent load
- More complex debugging (async stack traces)
- All database session usage must use `async with` pattern

## Compliance
New endpoint handlers and services must be async. Sync code inside async functions must use `asyncio.to_thread()` or `run_in_executor`.
