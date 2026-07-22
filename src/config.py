"""Runtime configuration for the Legal AI Pipeline.

Configuration is deliberately standard-library based so the service can start
in a minimal container. Production-like environments reject mock services and
unsafe CORS settings rather than quietly exposing a demo configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when runtime configuration is unsafe or incomplete."""


def _parse_bool(value: str, variable_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(
        f"{variable_name} must be one of true/false, 1/0, yes/no, or on/off"
    )


def _parse_positive_int(value: str, variable_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{variable_name} must be an integer") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{variable_name} must be greater than zero")
    return parsed


def _parse_origins(value: str) -> tuple[str, ...]:
    origins = tuple(
        origin.strip().rstrip("/")
        for origin in value.split(",")
        if origin.strip()
    )
    if not origins:
        raise ConfigurationError("CORS_ALLOW_ORIGINS must include at least one origin")
    return origins


@dataclass(frozen=True)
class AppSettings:
    """Validated settings loaded once at process startup."""

    environment: str
    mock_mode: bool
    allowed_origins: tuple[str, ...]
    max_upload_size_bytes: int
    upload_chunk_size_bytes: int
    retrieval_top_k: int
    confidence_threshold: float
    log_level: str
    enable_docs: bool

    @property
    def is_production_like(self) -> bool:
        return self.environment in {"staging", "production"}


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    """Load and validate settings from an environment mapping."""
    values = os.environ if environ is None else environ

    environment = values.get("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "staging", "production"}:
        raise ConfigurationError(
            "APP_ENV must be development, test, staging, or production"
        )

    mock_mode = _parse_bool(values.get("MOCK_MODE", "true"), "MOCK_MODE")
    allowed_origins = _parse_origins(
        values.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    )
    max_upload_size_bytes = _parse_positive_int(
        values.get("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)),
        "MAX_UPLOAD_SIZE_BYTES",
    )
    upload_chunk_size_bytes = _parse_positive_int(
        values.get("UPLOAD_CHUNK_SIZE_BYTES", str(1024 * 1024)),
        "UPLOAD_CHUNK_SIZE_BYTES",
    )
    retrieval_top_k = _parse_positive_int(
        values.get("RETRIEVAL_TOP_K", "5"), "RETRIEVAL_TOP_K"
    )

    try:
        confidence_threshold = float(values.get("CONFIDENCE_THRESHOLD", "0.8"))
    except ValueError as exc:
        raise ConfigurationError("CONFIDENCE_THRESHOLD must be a number") from exc
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ConfigurationError("CONFIDENCE_THRESHOLD must be between 0 and 1")

    log_level = values.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        raise ConfigurationError("LOG_LEVEL must be a standard Python logging level")

    enable_docs = _parse_bool(
        values.get("ENABLE_API_DOCS", "true" if environment == "development" else "false"),
        "ENABLE_API_DOCS",
    )

    settings = AppSettings(
        environment=environment,
        mock_mode=mock_mode,
        allowed_origins=allowed_origins,
        max_upload_size_bytes=max_upload_size_bytes,
        upload_chunk_size_bytes=upload_chunk_size_bytes,
        retrieval_top_k=retrieval_top_k,
        confidence_threshold=confidence_threshold,
        log_level=log_level,
        enable_docs=enable_docs,
    )

    if settings.is_production_like and settings.mock_mode:
        raise ConfigurationError(
            "MOCK_MODE must be false when APP_ENV is staging or production"
        )
    if settings.is_production_like and "*" in settings.allowed_origins:
        raise ConfigurationError(
            "CORS_ALLOW_ORIGINS cannot contain '*' in staging or production"
        )
    if settings.upload_chunk_size_bytes > settings.max_upload_size_bytes:
        raise ConfigurationError(
            "UPLOAD_CHUNK_SIZE_BYTES cannot exceed MAX_UPLOAD_SIZE_BYTES"
        )

    return settings


# Backward-compatible constants used by the core pipeline. New application
# code should receive AppSettings through dependency wiring instead.
_DEFAULT_SETTINGS = load_settings()
CONFIDENCE_THRESHOLD: float = _DEFAULT_SETTINGS.confidence_threshold
RETRIEVAL_TOP_K: int = _DEFAULT_SETTINGS.retrieval_top_k
REDLINE_TRIGGER_MIN_RISK = "medium"
MOCK_MODE: bool = _DEFAULT_SETTINGS.mock_mode