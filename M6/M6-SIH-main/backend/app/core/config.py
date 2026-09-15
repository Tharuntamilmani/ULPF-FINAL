"""
M6 Control Plane — Application Settings
All secrets come from environment variables. No hard-coded credentials.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Loaded once and cached."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_env: str = Field("development", pattern="^(development|staging|production)$")
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 1
    log_level: str = "INFO"

    # ── Security ───────────────────────────────────────────────────────────────
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── Initial admin (seed only) ──────────────────────────────────────────────
    admin_username: str = "admin"
    admin_email: str = "admin@ulpf.local"
    admin_password: str = Field(..., min_length=8)

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "m6_control_plane"
    postgres_user: str = "m6user"
    postgres_password: str = Field(...)
    database_pool_size: int = 10
    database_max_overflow: int = 20

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus

        pwd = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Used by Alembic (synchronous)."""
        from urllib.parse import quote_plus

        pwd = quote_plus(self.postgres_password)
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_config_ttl_seconds: int = 3600

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Kafka ──────────────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: str = ""
    kafka_sasl_username: str = ""
    kafka_sasl_password: str = ""
    kafka_config_topic: str = "ulpf.m6.config.updates"
    kafka_replay_topic: str = "ulpf.replay"
    kafka_enabled: bool = True

    # ── MinIO ──────────────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_bucket_contracts: str = "ulpf-contracts"
    minio_bucket_schemas: str = "ulpf-schemas"

    # ── OpenSearch ─────────────────────────────────────────────────────────────
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = ""
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False

    # ── Prometheus ─────────────────────────────────────────────────────────────
    prometheus_enabled: bool = True

    # ── Grafana ────────────────────────────────────────────────────────────────
    grafana_url: str = "http://localhost:3000"
    grafana_user: str = "admin"
    grafana_password: str = ""

    # ── External M1–M5 URLs ────────────────────────────────────────────────────
    m1_base_url: str = ""
    m2_base_url: str = ""
    m3_base_url: str = ""
    m4_base_url: str = ""
    m5_base_url: str = ""
    external_health_timeout_seconds: int = 5
    external_health_retry_attempts: int = 2

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allow_credentials: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(o) for o in v]
        if isinstance(v, str):
            v = v.strip()
            # Handle JSON array format: ["url1","url2"]
            if v.startswith("["):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(o) for o in parsed]
                except Exception:
                    pass
            # Handle comma-separated format
            return [o.strip() for o in v.split(",") if o.strip()]
        return []

    # ── Feature flags ─────────────────────────────────────────────────────────
    use_mock_adapters: bool = False
    enable_audit_log: bool = True
    enable_config_distribution: bool = True
    enable_replay: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Import this wherever settings are needed."""
    return Settings()
