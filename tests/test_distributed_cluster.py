"""Tests for the read-only distributed cluster monitor."""

from types import SimpleNamespace

from app.distributed.cluster import ClusterMonitor
from app.distributed.config import load_settings


class FakeRedis:
    def __init__(self, *, online: bool = True, queued: int = 0) -> None:
        self.online = online
        self.queued = queued

    def ping(self) -> bool:
        if not self.online:
            raise ConnectionError("offline")
        return True

    def llen(self, queue_name: str) -> int:
        assert queue_name == "celery"
        return self.queued


class FakeStorage:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def buckets_ready(self) -> bool:
        return self.ready


class FakeInspect:
    def __init__(self, active) -> None:
        self._active = active

    def active(self):
        return self._active


class FakeControl:
    def __init__(self, active) -> None:
        self.active = active
        self.timeout = None

    def inspect(self, *, timeout: float):
        self.timeout = timeout
        return FakeInspect(self.active)


def test_cluster_snapshot_reports_queue_and_worker_activity() -> None:
    control = FakeControl(
        {
            "worker@node-b": [],
            "worker@node-a": [{"id": "job-1"}],
        }
    )
    celery = SimpleNamespace(
        conf=SimpleNamespace(task_default_queue=None),
        control=control,
    )
    monitor = ClusterMonitor(
        load_settings(),
        celery,
        FakeStorage(),
        FakeRedis(queued=3),
    )

    status = monitor.snapshot()

    assert status.api == "online"
    assert status.redis == "online"
    assert status.minio == "online"
    assert status.queue_depth == 3
    assert [worker.worker_id for worker in status.workers] == [
        "worker@node-a",
        "worker@node-b",
    ]
    assert status.workers[0].status == "busy"
    assert status.workers[0].active_job_ids == ["job-1"]
    assert status.workers[1].status == "idle"
    assert control.timeout == 1.0


def test_cluster_snapshot_keeps_service_failures_independent() -> None:
    celery = SimpleNamespace(
        conf=SimpleNamespace(task_default_queue=None),
        control=FakeControl({}),
    )
    monitor = ClusterMonitor(
        load_settings(),
        celery,
        FakeStorage(ready=False),
        FakeRedis(online=False),
    )

    status = monitor.snapshot()

    assert status.redis == "offline"
    assert status.minio == "offline"
    assert status.queue_depth is None
    assert status.workers == []
