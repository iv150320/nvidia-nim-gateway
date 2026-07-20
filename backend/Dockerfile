# ── NVIDIA NIM Gateway — Docker Image ─────────────────────────────────
# Multi-stage build for minimal production image.

# ── Stage 1: Dependencies ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────
FROM python:3.12-slim

# Runtime deps only (keep slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN addgroup --system --gid 1001 nim && \
    adduser --system --uid 1001 --gid 1001 nim

WORKDIR /app

# Copy application code
COPY nim_gateway/ /app/nim_gateway/
COPY config/ /app/config/

# Copy config defaults
COPY requirements.txt /app/

# Ownership
RUN chown -R nim:nim /app

USER nim

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run with uvicorn
CMD ["uvicorn", "nim_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
