"""Read-only monitoring for the Pixora distributed processing cluster."""

import logging
from typing import Any

from celery import Celery
from redis import Redis

from app.distributed.config import DistributedSettings
from app.distributed.contracts import (
    ClusterStatusResponse,
    ClusterWorkerStatus,
)
from app.distributed.storage import ObjectStorage


logger = logging.getLogger(__name__)


class ClusterMonitor:
    """Collect a small, UI-friendly snapshot without changing cluster state."""

    def __init__(
        self,
        settings: DistributedSettings,
        celery: Celery,
        storage: ObjectStorage,
        redis_client: Redis | None = None,
    ) -> None:
        self.celery = celery
        self.storage = storage
        self.redis_client = redis_client or Redis.from_url(
            settings.redis_broker_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def snapshot(self) -> ClusterStatusResponse:
        """Return independent health and workload information for every node."""
        redis_status = "offline"
        queue_depth: int | None = None
        workers: list[ClusterWorkerStatus] = []

        try:
            if self.redis_client.ping():
                redis_status = "online"
                queue_name = str(self.celery.conf.task_default_queue or "celery")
                queue_depth = int(self.redis_client.llen(queue_name))
                workers = self._workers()
        except Exception as error:
            logger.warning("Redis cluster monitor failed: %s", error)

        minio_status = "offline"
        try:
            if self.storage.buckets_ready():
                minio_status = "online"
        except Exception as error:
            logger.warning("MinIO cluster monitor failed: %s", error)

        return ClusterStatusResponse(
            redis=redis_status,
            minio=minio_status,
            queue_depth=queue_depth,
            workers=workers,
        )

    def _workers(self) -> list[ClusterWorkerStatus]:
        """Use one Celery inspection round trip to discover active workers."""
        inspector = self.celery.control.inspect(timeout=1.0)
        active_by_worker: dict[str, list[dict[str, Any]]] = inspector.active() or {}
        workers = []
        for worker_id in sorted(active_by_worker):
            active_jobs = active_by_worker.get(worker_id) or []
            job_ids = [
                str(job["id"])
                for job in active_jobs
                if isinstance(job, dict) and job.get("id")
            ]
            workers.append(
                ClusterWorkerStatus(
                    worker_id=worker_id,
                    status="busy" if job_ids else "idle",
                    active_tasks=len(job_ids),
                    active_job_ids=job_ids,
                )
            )
        return workers
