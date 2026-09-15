from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Security & Authentication
    api_auth_token: str = "changeme_in_env_file"

    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw: str = "ulpf.raw"
    kafka_topic_dlq: str = "ulpf.dlq"
    kafka_topic_replay: str = "ulpf.replay"

    # MinIO Raw Vault Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "ulpf-raw"
    minio_secure: bool = False

    # Listener Ports & Host Binding
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    udp_port: int = 514
    tcp_port: int = 515

    # Payload & Queue Limits
    max_http_payload_bytes: int = 2 * 1024 * 1024  # 2MB max payload
    udp_queue_size: int = 10000
    udp_workers: int = 4
    outbox_db_path: str = "data/outbox.db"
    kafka_acks: str = "all"
    kafka_enable_idempotence: bool = True
    kafka_compression_type: str = "gzip"

    # Rate Limiting (Token Bucket)
    max_events_per_second: float = 1000.0
    burst_size: float = 2000.0

    # Metadata Defaults
    default_tenant_id: str = "demo-tenant"
    default_source_id: str = "collector-source-01"
    default_source_type: str = "firewall"
    default_ingest_zone: str = "dmz"
    default_collector_id: str = "collector-01"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
