"""Tests for coordinator behavior that must remain safe under partial failure."""

import app.distributed.api as api_module
from fastapi import HTTPException
import pytest
from app.distributed.contracts import (
    BatchJob,
    BatchManifest,
    ClusterStatusResponse,
    JobStatusResponse,
    OutputDetails,
    ProcessingOptionsPayload,
)


def test_cluster_endpoint_returns_monitor_snapshot(monkeypatch) -> None:
    expected = ClusterStatusResponse(
        redis="online",
        minio="online",
        queue_depth=2,
        workers=[],
    )
    monkeypatch.setattr(api_module.cluster_monitor, "snapshot", lambda: expected)

    assert api_module.get_cluster_status() == expected


def test_partial_dispatch_keeps_every_job_trackable(monkeypatch) -> None:
    manifest = BatchManifest(
        batch_id="batch-1",
        jobs=[
            BatchJob(
                job_id=f"job-{index}",
                filename=f"image-{index}.png",
                source_object=f"batch-1/job-{index}/image.png",
            )
            for index in range(3)
        ],
    )
    calls: list[str] = []
    saved: list[BatchManifest] = []

    def apply_async(*, task_id, **_kwargs) -> None:
        calls.append(task_id)
        if task_id == "job-1":
            raise ConnectionError("broker unavailable")

    monkeypatch.setattr(api_module.process_image_task, "apply_async", apply_async)
    monkeypatch.setattr(
        api_module.batch_repository,
        "save",
        lambda value: saved.append(value.model_copy(deep=True)),
    )

    failed = api_module._dispatch_jobs(
        manifest,
        ProcessingOptionsPayload(width=100, height=100),
    )

    assert calls == ["job-0", "job-1"]
    assert failed == 2
    assert manifest.jobs[0].dispatch_error is None
    assert manifest.jobs[1].dispatch_error is not None
    assert manifest.jobs[2].dispatch_error is not None
    assert saved[-1].jobs[2].dispatch_error is not None


def test_dispatch_failure_is_returned_without_querying_celery() -> None:
    job = BatchJob(
        job_id="job-1",
        filename="image.png",
        source_object="batch-1/job-1/image.png",
        dispatch_error="Не удалось поставить задачу в очередь",
    )

    status = api_module._job_status(job)

    assert status.status == "FAILURE"
    assert status.progress == 100
    assert status.error == "Не удалось поставить задачу в очередь"


def test_batch_status_aggregates_all_terminal_states(monkeypatch) -> None:
    manifest = BatchManifest(
        batch_id="batch-1",
        jobs=[
            BatchJob(
                job_id="job-1",
                filename="one.png",
                source_object="one.png",
            ),
            BatchJob(
                job_id="job-2",
                filename="two.png",
                source_object="two.png",
            ),
        ],
    )
    monkeypatch.setattr(api_module.batch_repository, "get", lambda _id: manifest)
    monkeypatch.setattr(
        api_module,
        "_job_status",
        lambda job: JobStatusResponse(
            job_id=job.job_id,
            filename=job.filename,
            status="SUCCESS" if job.job_id == "job-1" else "REVOKED",
            progress=100,
        ),
    )

    status = api_module.get_batch_status("batch-1")

    assert status.total == 2
    assert status.completed == 1
    assert status.failed == 0
    assert status.cancelled == 1
    assert status.pending == 0
    assert status.progress == 100


def test_cancel_batch_is_durable_when_revoke_broadcast_fails(monkeypatch) -> None:
    manifest = BatchManifest(
        batch_id="batch-1",
        jobs=[
            BatchJob(
                job_id="job-1",
                filename="one.png",
                source_object="one.png",
            )
        ],
    )
    events: list[str] = []
    monkeypatch.setattr(api_module.batch_repository, "get", lambda _id: manifest)
    monkeypatch.setattr(
        api_module.batch_repository,
        "save",
        lambda _manifest: events.append("saved"),
    )

    def job_status(job: BatchJob) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=job.job_id,
            filename=job.filename,
            status="REVOKED" if job.cancelled else "PENDING",
            progress=100 if job.cancelled else 0,
        )

    def failed_revoke(*_args, **_kwargs) -> None:
        events.append("revoke")
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(api_module, "_job_status", job_status)
    monkeypatch.setattr(api_module.celery_app.control, "revoke", failed_revoke)

    status = api_module.cancel_batch("batch-1")

    assert events == ["saved", "revoke"]
    assert manifest.jobs[0].cancelled is True
    assert status.jobs[0].status == "REVOKED"
    assert status.cancelled == 1


def test_download_maps_storage_outage_to_service_unavailable(monkeypatch) -> None:
    job = BatchJob(
        job_id="job-1",
        filename="one.png",
        source_object="one.png",
    )
    monkeypatch.setattr(api_module, "_find_job", lambda _job_id: job)
    monkeypatch.setattr(
        api_module,
        "_job_status",
        lambda _job: JobStatusResponse(
            job_id="job-1",
            filename="one.png",
            status="SUCCESS",
            progress=100,
            output=OutputDetails(
                object_name="batch/job/result.webp",
                filename="result.webp",
                format="WEBP",
                width=10,
                height=10,
                size=100,
                worker="worker@node",
            ),
        ),
    )
    monkeypatch.setattr(
        api_module.storage,
        "open_result",
        lambda _name: (_ for _ in ()).throw(ConnectionError("offline")),
    )

    with pytest.raises(HTTPException) as raised:
        api_module.download_result("job-1")

    assert raised.value.status_code == 503
