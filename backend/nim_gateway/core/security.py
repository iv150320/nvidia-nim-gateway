"""API key authentication & optional JWT support."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import HTTPException, Request, status


def validate_api_key(request: Request, api_keys: dict[str, str]) -> str:
    """Extract and validate the API key from Authorization header.

    Returns the key label on success.
    Raises 401 on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Use: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key = auth_header.removeprefix("Bearer ").strip()
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks
    for stored_key, label in api_keys.items():
        if hmac.compare_digest(provided_key, stored_key):
            return label

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return f"nvgw_{secrets.token_hex(32)}"


def hash_key(key: str) -> str:
    """Return a SHA-256 digest for logging (never log raw keys)."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]
