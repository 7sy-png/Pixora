"""Tests for MinIO bucket readiness and automatic object retention."""

from app.distributed.config import DistributedSettings
from app.distributed.storage import ObjectStorage


class RecordingMinio:
    def __init__(self, existing: set[str] | None = None) -> None:
        self.existing = existing or set()
        self.created: list[str] = []
        self.lifecycle = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.existing

    def make_bucket(self, bucket: str) -> None:
        self.existing.add(bucket)
        self.created.append(bucket)

    def set_bucket_lifecycle(self, bucket: str, config) -> None:
        self.lifecycle[bucket] = config


def _settings() -> DistributedSettings:
    return DistributedSettings(
        redis_broker_url="redis://localhost/0",
        redis_result_url="redis://localhost/1",
        redis_metadata_url="redis://localhost/2",
        minio_endpoint="localhost:9000",
        minio_access_key="pixora",
        minio_secret_key="secret",
        minio_secure=False,
        minio_input_bucket="inputs",
        minio_result_bucket="results",
        max_batch_files=50,
        max_batch_size_bytes=200 * 1024 * 1024,
        result_expires_seconds=24 * 60 * 60,
    )


def test_storage_initializes_buckets_with_one_day_retention() -> None:
    client = RecordingMinio()
    storage = ObjectStorage(_settings(), client=client)

    assert storage.buckets_ready() is False

    storage.ensure_buckets()

    assert storage.buckets_ready() is True
    assert client.created == ["inputs", "results"]
    assert set(client.lifecycle) == {"inputs", "results"}
    for lifecycle in client.lifecycle.values():
        assert lifecycle.rules[0].expiration.days == 1
