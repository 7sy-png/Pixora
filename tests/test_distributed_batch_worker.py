"""Tests for Qt workers that communicate with the distributed API."""

from pathlib import Path

from app.models import ProcessingOptions
from app.workers import (
    DistributedBatchWorker,
    DistributedClusterWorker,
    DistributedDownloadWorker,
)


class CompletingClient:
    """Deterministic remote client double with one progress transition."""

    def __init__(self) -> None:
        self.status_calls = 0

    def check_health(self) -> bool:
        return True

    def submit_batch(self, _paths, _options):
        return {"batch_id": "batch-1", "total": 1, "jobs": []}

    def get_batch_status(self, _batch_id):
        self.status_calls += 1
        state = "PENDING" if self.status_calls == 1 else "SUCCESS"
        return {
            "batch_id": "batch-1",
            "jobs": [{"job_id": "job-1", "status": state}],
        }

    def get_cluster_status(self):
        return {
            "api": "online",
            "redis": "online",
            "minio": "online",
            "queue_depth": 0,
            "workers": [],
        }


def test_distributed_worker_polls_until_all_jobs_are_terminal() -> None:
    client = CompletingClient()
    worker = DistributedBatchWorker(
        client,
        [Path("source.png")],
        ProcessingOptions(10, 10),
        poll_interval_seconds=0,
        cluster_poll_interval_seconds=0,
    )
    submitted = []
    progress = []
    finished = []
    cluster = []
    worker.signals.submitted.connect(submitted.append)
    worker.signals.progress.connect(progress.append)
    worker.signals.finished.connect(finished.append)
    worker.signals.cluster.connect(cluster.append)

    worker.run()

    assert submitted[0]["batch_id"] == "batch-1"
    assert [item["jobs"][0]["status"] for item in progress] == [
        "PENDING",
        "SUCCESS",
    ]
    assert finished[0]["jobs"][0]["status"] == "SUCCESS"
    assert cluster[-1]["api"] == "online"


def test_cluster_worker_fetches_one_snapshot() -> None:
    client = CompletingClient()
    worker = DistributedClusterWorker(client)
    completed = []
    worker.signals.finished.connect(completed.append)

    worker.run()

    assert completed[0]["redis"] == "online"


class CancellingClient:
    def __init__(self) -> None:
        self.cancelled_batch: str | None = None

    def check_health(self) -> bool:
        return True

    def submit_batch(self, _paths, _options):
        return {"batch_id": "batch-1", "total": 1, "jobs": []}

    def cancel_batch(self, batch_id):
        self.cancelled_batch = batch_id
        return {
            "batch_id": batch_id,
            "jobs": [{"job_id": "job-1", "status": "REVOKED"}],
        }


def test_distributed_worker_cancels_remote_batch() -> None:
    client = CancellingClient()
    worker = DistributedBatchWorker(
        client,
        [Path("source.png")],
        ProcessingOptions(10, 10),
        poll_interval_seconds=0,
    )
    progress = []
    cancelled = []
    worker.signals.progress.connect(progress.append)
    worker.signals.cancelled.connect(lambda: cancelled.append(True))

    worker.cancel(remote=True)
    worker.run()

    assert client.cancelled_batch == "batch-1"
    assert progress[-1]["jobs"][0]["status"] == "REVOKED"
    assert cancelled == [True]


class DownloadingClient:
    def __init__(self) -> None:
        self.destinations = []

    def download_result(self, _job_id, destination):
        destination.write_bytes(b"result")
        self.destinations.append(destination)
        return destination


def test_download_worker_preserves_existing_files(tmp_path) -> None:
    (tmp_path / "image_pixora.webp").write_bytes(b"existing")
    client = DownloadingClient()
    jobs = [
        {
            "job_id": "job-1",
            "status": "SUCCESS",
            "output": {"filename": "image_pixora.webp"},
        },
        {
            "job_id": "job-2",
            "status": "FAILURE",
            "output": None,
        },
    ]
    worker = DistributedDownloadWorker(client, jobs, tmp_path)
    completed = []
    worker.signals.finished.connect(completed.append)

    worker.run()

    assert (tmp_path / "image_pixora.webp").read_bytes() == b"existing"
    assert client.destinations == [tmp_path / "image_pixora_2.webp"]
    assert completed == [[tmp_path / "image_pixora_2.webp"]]
