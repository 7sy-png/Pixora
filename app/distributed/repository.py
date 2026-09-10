"""Redis persistence for batch membership metadata."""

from redis import Redis

from app.distributed.config import DistributedSettings
from app.distributed.contracts import BatchJob, BatchManifest


class BatchRepository:
    """Persist batch manifests separately from transient Celery states."""

    KEY_PREFIX = "pixora:batch:"
    JOB_KEY_PREFIX = "pixora:job:"

    def __init__(
        self,
        settings: DistributedSettings,
        client: Redis | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or Redis.from_url(
            settings.redis_metadata_url,
            decode_responses=True,
        )

    def ping(self) -> bool:
        """Check that the metadata Redis database is reachable."""
        return bool(self.client.ping())

    def save(self, manifest: BatchManifest) -> None:
        """Store a manifest with the same lifetime as Celery results."""
        with self.client.pipeline(transaction=True) as pipeline:
            pipeline.setex(
                self._batch_key(manifest.batch_id),
                self.settings.result_expires_seconds,
                manifest.model_dump_json(),
            )
            for job in manifest.jobs:
                pipeline.setex(
                    self._job_key(job.job_id),
                    self.settings.result_expires_seconds,
                    job.model_dump_json(),
                )
            pipeline.execute()

    def get(self, batch_id: str) -> BatchManifest | None:
        """Load one manifest or return None after expiration."""
        serialized = self.client.get(self._batch_key(batch_id))
        if serialized is None:
            return None
        return BatchManifest.model_validate_json(serialized)

    def get_job(self, job_id: str) -> BatchJob | None:
        """Load one known task identity or return None after expiration."""
        serialized = self.client.get(self._job_key(job_id))
        if serialized is None:
            return None
        return BatchJob.model_validate_json(serialized)

    def _batch_key(self, batch_id: str) -> str:
        return f"{self.KEY_PREFIX}{batch_id}"

    def _job_key(self, job_id: str) -> str:
        return f"{self.JOB_KEY_PREFIX}{job_id}"
