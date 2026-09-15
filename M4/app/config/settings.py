"""Application and environment settings for ULPF M4."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime service settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(env_prefix="M4_", case_sensitive=False)

    app_name: str = "ULPF-M4-Enrichment-Engine"
    environment: str = "production"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8004
    api_auth_secret: str = Field(
        default="m4-insecure-secret-key-change-in-prod-8f2c3d4e5f6a7b8c",
        description="Shared secret or signing key for API tokens",
    )
    default_cache_ttl_seconds: int = 300
    cache_max_size: int = 10000
    default_provider_timeout_seconds: float = 2.0
    max_pipeline_concurrency: int = 8
    metrics_enabled: bool = True
