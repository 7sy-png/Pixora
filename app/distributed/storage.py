"""Small MinIO adapter used by both API and Celery workers."""

from io import BytesIO
from math import ceil
from typing import BinaryIO

from minio.commonconfig import Filter
from minio.lifecycleconfig import Expiration, LifecycleConfig, Rule
from minio import Minio

from app.distributed.config import DistributedSettings


class ObjectStorage:
    """Store source and processed images outside the task queue."""

    def __init__(
        self,
        settings: DistributedSettings,
        client: Minio | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_buckets(self) -> None:
        """Create required buckets and apply automatic object expiration."""
        for bucket in (
            self.settings.minio_input_bucket,
            self.settings.minio_result_bucket,
        ):
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
            self.client.set_bucket_lifecycle(
                bucket,
                self._lifecycle_config(),
            )

    def buckets_ready(self) -> bool:
        """Check required buckets without mutating storage during health probes."""
        return all(
            self.client.bucket_exists(bucket)
            for bucket in (
                self.settings.minio_input_bucket,
                self.settings.minio_result_bucket,
            )
        )

    def put_source(
        self,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Upload one original image."""
        self._put(
            self.settings.minio_input_bucket,
            object_name,
            data,
            content_type,
        )

    def put_result(
        self,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Upload one processed image."""
        self._put(
            self.settings.minio_result_bucket,
            object_name,
            data,
            content_type,
        )

    def get_source(self, object_name: str) -> bytes:
        """Download a complete source image for processing."""
        response = self.client.get_object(
            self.settings.minio_input_bucket,
            object_name,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def open_result(self, object_name: str) -> BinaryIO:
        """Open a streaming response for a processed image."""
        return self.client.get_object(
            self.settings.minio_result_bucket,
            object_name,
        )

    def delete_source(self, object_name: str) -> None:
        """Remove a source after success or failed batch creation cleanup."""
        self.client.remove_object(
            self.settings.minio_input_bucket,
            object_name,
        )

    def _lifecycle_config(self) -> LifecycleConfig:
        """Expire dedicated Pixora objects after the result metadata lifetime."""
        expiration_days = max(
            1,
            ceil(self.settings.result_expires_seconds / (24 * 60 * 60)),
        )
        return LifecycleConfig(
            [
                Rule(
                    status="Enabled",
                    rule_filter=Filter(prefix=""),
                    rule_id="pixora-retention",
                    expiration=Expiration(days=expiration_days),
                )
            ]
        )

    def _put(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Upload in-memory bytes with a known content length."""
        self.client.put_object(
            bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
