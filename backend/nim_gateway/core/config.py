"""Application configuration — loaded from YAML files and environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# YAML-backed models
# ---------------------------------------------------------------------------

class NIMProviderConfig(BaseModel):
    """Single NVIDIA NIM provider endpoint."""

    name: str
    base_url: str
    api_key: str | None = None
    weight: int = 1
    timeout: float = 120.0
    max_retries: int = 2
    enabled: bool = True


class ModelRoute(BaseModel):
    """Map a public-facing model name to internal providers with fallback chain."""

    model: str
    providers: List[str]  # ordered provider names for fallback
    max_tokens: int = 4096
    rpm_limit: int = 60
    tpm_limit: int | None = None  # tokens per minute


class GatewayConfig(BaseModel):
    """Top-level gateway YAML schema."""

    version: str = "1.0"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # API key validation
    api_key_enabled: bool = True
    api_keys: Dict[str, str] = Field(default_factory=dict)  # key -> label

    @field_validator("api_keys", mode="before")
    @classmethod
    def coerce_api_keys(cls, v: Any) -> Dict[str, str]:
        if v is None:
            return {}
        return v

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: int = 60  # requests per minute

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_max_size: int = 512

    # Circuit breaker defaults
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 30
    circuit_breaker_half_open_max_calls: int = 3

    # OpenTelemetry
    otlp_endpoint: str | None = None
    service_name: str = "nvidia-nim-gateway"

    # Prometheus
    metrics_enabled: bool = True


class ModelsConfig(BaseModel):
    """models.yaml schema."""

    providers: Dict[str, NIMProviderConfig] = Field(default_factory=dict)
    routes: Dict[str, ModelRoute] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Environment + file-driven settings.  Pydantic v2 BaseSettings
    reads env vars automatically."""

    # Paths
    config_dir: str = str(Path(__file__).resolve().parent.parent.parent.parent / "config")

    gateway_file: str = "gateway.yaml"
    models_file: str = "models.yaml"

    # Overrides via env
    log_level: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None

    # Quick override for development
    nim_api_key: Optional[str] = None
    nim_base_url: Optional[str] = None

    model_config = {"env_prefix": "NIM_GW_", "case_sensitive": False}

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    _gateway: GatewayConfig | None = None
    _models: ModelsConfig | None = None

    @property
    def gateway(self) -> GatewayConfig:
        if self._gateway is None:
            self._gateway = self._load_yaml(self.gateway_file, GatewayConfig)
        return self._gateway

    @property
    def models(self) -> ModelsConfig:
        if self._models is None:
            self._models = self._load_yaml(self.models_file, ModelsConfig)
        return self._models

    def _load_yaml(self, filename: str, model_cls: type) -> Any:
        path = Path(self.config_dir) / filename
        if not path.exists():
            # Return defaults
            return model_cls()
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return model_cls(**raw)

    def reload(self) -> None:
        """Force reload configs from disk (useful after hot-reload)."""
        self._gateway = None
        self._models = None
        # Re-read
        _ = self.gateway, self.models


# Global singleton
settings = Settings()
