"""Central configuration loader (Stage 9).

Provides a typed, centralized interface for environment configuration.
Other modules should import get_config() and avoid direct os.getenv calls
(except in very low-level bootstrap code / validator scripts).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

_ALLOWED_PROVIDERS = {"openai", "ollama", "dummy"}


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(',') if item.strip()]


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    db: str
    url: Optional[str] = None


@dataclass
class ProviderConfig:
    name: str
    openai_api_key: Optional[str]
    openai_model: str
    ollama_base_url: str
    ollama_model: str


@dataclass
class EmbeddingRuntimeConfig:
    timeout: float
    max_retries: int
    retry_backoff: float


@dataclass
class SearchConfig:
    distance_threshold: float


@dataclass
class ChunkingConfig:
    strategy: str
    size: int


@dataclass
class LoggingConfig:
    level: str
    format: str = "plain"

    @property
    def debug_enabled(self) -> bool:
        return self.level.upper() == "DEBUG"


@dataclass
class CORSConfig:
    allowed_origins: List[str] = field(default_factory=list)


@dataclass
class ServiceMeta:
    version: str
    service_name: str = "searchapi"


@dataclass
class AppConfig:
    environment: str
    database: DatabaseConfig
    provider: ProviderConfig
    embedding: EmbeddingRuntimeConfig
    search: SearchConfig
    chunking: ChunkingConfig
    logging: LoggingConfig
    cors: CORSConfig
    service: ServiceMeta

    def to_safe_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Mask sensitive
        data['database']['password'] = '***'
        if data['provider'].get('openai_api_key'):
            data['provider']['openai_api_key'] = '***'
        return data


_singleton: Optional[AppConfig] = None


def load_config(env: Optional[Dict[str, str]] = None) -> AppConfig:
    e = env or os.environ

    environment = e.get("ENVIRONMENT", "local")
    provider_name = e.get("PROVIDER", "dummy")
    if provider_name not in _ALLOWED_PROVIDERS:
        raise ValueError(f"Invalid PROVIDER '{provider_name}' (allowed: {', '.join(sorted(_ALLOWED_PROVIDERS))})")

    # Database
    db_cfg = DatabaseConfig(
        host=e.get("POSTGRES_HOST", "localhost"),
        port=int(e.get("POSTGRES_PORT", "5432")),
        user=e.get("POSTGRES_USER", "postgres"),
        password=e.get("POSTGRES_PASSWORD", ""),
        db=e.get("POSTGRES_DB", "dhodb"),
        url=e.get("DATABASE_URL") or None,
    )

    # Provider specifics
    provider_cfg = ProviderConfig(
        name=provider_name,
        openai_api_key=e.get("OPENAI_API_KEY"),
        openai_model=e.get("OPENAI_MODEL", "text-embedding-3-small"),
        ollama_base_url=e.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        ollama_model=e.get("OLLAMA_MODEL", "nomic-embed-text"),
    )

    embedding_cfg = EmbeddingRuntimeConfig(
        timeout=float(e.get("EMBEDDING_TIMEOUT", "30")),
        max_retries=int(e.get("EMBEDDING_MAX_RETRIES", "1")),
        retry_backoff=float(e.get("EMBEDDING_RETRY_BACKOFF", "0.5")),
    )

    # Clamp or at least parse distance threshold
    try:
        dt = float(e.get("DISTANCE_THRESHOLD", "0.5"))
    except ValueError:
        dt = 0.5
    search_cfg = SearchConfig(distance_threshold=dt)

    chunking_cfg = ChunkingConfig(
        strategy=e.get("CHUNKING_STRATEGY", "sentence_splitter"),
        size=int(e.get("CHUNK_SIZE", "500")),
    )

    logging_cfg = LoggingConfig(level=e.get("LOG_LEVEL", "INFO"))
    cors_cfg = CORSConfig(allowed_origins=_split_csv(e.get("TILLADTE_KALDERE", "")))
    service_meta = ServiceMeta(version=e.get("SERVICE_VERSION", "0.0.0"))

    return AppConfig(
        environment=environment,
        database=db_cfg,
        provider=provider_cfg,
        embedding=embedding_cfg,
        search=search_cfg,
        chunking=chunking_cfg,
        logging=logging_cfg,
        cors=cors_cfg,
        service=service_meta,
    )


def get_config() -> AppConfig:
    global _singleton
    if _singleton is None:
        _singleton = load_config()
    return _singleton


def refresh_config() -> AppConfig:
    global _singleton
    _singleton = load_config()
    return _singleton
