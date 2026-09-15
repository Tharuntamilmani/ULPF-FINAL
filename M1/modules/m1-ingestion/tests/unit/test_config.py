from app.config.settings import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.api_auth_token == "changeme_in_env_file"
    assert settings.kafka_topic_raw == "ulpf.raw"
    assert settings.minio_bucket_raw == "ulpf-raw"
    assert settings.http_port == 8000
    assert settings.udp_port == 514
    assert settings.tcp_port == 515
