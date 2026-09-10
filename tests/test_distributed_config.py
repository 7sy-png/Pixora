"""Tests for explicit environment configuration parsing."""

import pytest

from app.distributed.config import load_settings


def test_distributed_settings_use_local_development_defaults(monkeypatch) -> None:
    for variable in (
        "PIXORA_REDIS_BROKER_URL",
        "PIXORA_MINIO_ENDPOINT",
        "PIXORA_MINIO_SECURE",
        "PIXORA_MAX_BATCH_FILES",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = load_settings()

    assert settings.redis_broker_url == "redis://localhost:6379/0"
    assert settings.minio_endpoint == "localhost:9000"
    assert settings.minio_secure is False
    assert settings.max_batch_files == 50


def test_distributed_settings_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("PIXORA_MINIO_SECURE", "yes")
    monkeypatch.setenv("PIXORA_MAX_BATCH_FILES", "12")

    settings = load_settings()

    assert settings.minio_secure is True
    assert settings.max_batch_files == 12


def test_distributed_settings_reject_invalid_boolean(monkeypatch) -> None:
    monkeypatch.setenv("PIXORA_MINIO_SECURE", "sometimes")

    with pytest.raises(ValueError, match="true или false"):
        load_settings()
