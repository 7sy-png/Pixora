"""FastAPI coordinator for Pixora distributed batch processing."""

from asyncio import to_thread
from collections.abc import Iterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Annotated, BinaryIO
from urllib.parse import quote
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app import __version__
from app.distributed.celery_app import celery_app
from app.distributed.config import load_settings
from app.distributed.contracts import (
    BatchCreatedResponse,
    BatchJob,
    BatchManifest,
    BatchStatusResponse,
    JobAccepted,
    JobStatusResponse,
    OutputDetails,
    ProcessingOptionsPayload,
)
from app.distributed.repository import BatchRepository
from app.distributed.storage import ObjectStorage
from app.distributed.tasks import process_image_task
from app.utils.validation import (
    MAX_IMAGE_SIZE_BYTES,
    ImageValidationError,
    validate_image_bytes,
)


settings = load_settings()
storage = ObjectStorage(settings)
batch_repository = BatchRepository(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Verify backing services and create buckets before accepting work."""
    batch_repository.ping()
    storage.ensure_buckets()
    yield


app = FastAPI(
    title="Pixora Distributed API",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report readiness of Redis and MinIO."""
    try:
        batch_repository.ping()
        if not storage.buckets_ready():
            raise RuntimeError("required MinIO buckets are missing")
    except Exception as error:
        logger.warning("Distributed health check failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed services are unavailable",
        ) from error
    return {"status": "ok"}


@app.post(
    "/api/v1/batches",
    response_model=BatchCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_batch(
    files: Annotated[list[UploadFile], File(description="Image files")],
    options: Annotated[str, Form(description="Processing options as JSON")],
) -> BatchCreatedResponse:
    """Validate a batch, store originals and enqueue one task per image."""
    try:
        payload = ProcessingOptionsPayload.model_validate_json(options)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_url=False),
        ) from error

    if not files:
        raise HTTPException(status_code=422, detail="Не выбраны изображения")
    if len(files) > settings.max_batch_files:
        raise HTTPException(
            status_code=413,
            detail=f"В одном пакете допускается не более {settings.max_batch_files} файлов",
        )

    batch_id = str(uuid4())
    jobs: list[BatchJob] = []
    uploaded_objects: list[str] = []
    total_size = 0
    try:
        for upload in files:
            raw_filename = (upload.filename or "image").replace("\\", "/")
            filename = Path(raw_filename.rsplit("/", 1)[-1]).name
            data = await upload.read(MAX_IMAGE_SIZE_BYTES + 1)
            validate_image_bytes(data, filename=filename)
            total_size += len(data)
            if total_size > settings.max_batch_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Суммарный размер пакета превышает допустимый предел",
                )

            job_id = str(uuid4())
            source_object = f"{batch_id}/{job_id}/{filename}"
            content_type = upload.content_type or "application/octet-stream"
            await to_thread(
                storage.put_source,
                source_object,
                data,
                content_type,
            )
            uploaded_objects.append(source_object)
            jobs.append(
                BatchJob(
                    job_id=job_id,
                    filename=filename,
                    source_object=source_object,
                )
            )
    except ImageValidationError as error:
        await to_thread(_delete_sources, uploaded_objects)
        raise HTTPException(status_code=422, detail=f"{filename}: {error}") from error
    except HTTPException:
        await to_thread(_delete_sources, uploaded_objects)
        raise
    except Exception as error:
        await to_thread(_delete_sources, uploaded_objects)
        logger.exception("Failed to upload batch %s", batch_id)
        raise HTTPException(
            status_code=503,
            detail="Не удалось загрузить пакет в хранилище",
        ) from error

    try:
        manifest = BatchManifest(batch_id=batch_id, jobs=jobs)
        await to_thread(batch_repository.save, manifest)
    except Exception as error:
        await to_thread(_delete_sources, uploaded_objects)
        logger.exception("Failed to persist batch %s", batch_id)
        raise HTTPException(
            status_code=503,
            detail="Не удалось сохранить сведения о пакете",
        ) from error

    failed_to_enqueue = await to_thread(_dispatch_jobs, manifest, payload)
    return BatchCreatedResponse(
        batch_id=batch_id,
        total=len(jobs),
        failed_to_enqueue=failed_to_enqueue,
        jobs=[
            JobAccepted(
                job_id=job.job_id,
                filename=job.filename,
                queued=job.dispatch_error is None,
                error=job.dispatch_error,
            )
            for job in jobs
        ],
    )


@app.get(
    "/api/v1/batches/{batch_id}",
    response_model=BatchStatusResponse,
)
def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """Return aggregate progress and individual worker attribution."""
    manifest = batch_repository.get(batch_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Пакет не найден")

    jobs = [_job_status(job) for job in manifest.jobs]
    completed = sum(job.status == "SUCCESS" for job in jobs)
    failed = sum(job.status == "FAILURE" for job in jobs)
    cancelled = sum(job.status == "REVOKED" for job in jobs)
    processing = sum(
        job.status in {"RECEIVED", "STARTED", "PROCESSING", "RETRY"}
        for job in jobs
    )
    pending = len(jobs) - completed - failed - cancelled - processing
    progress = round(sum(job.progress for job in jobs) / len(jobs))
    return BatchStatusResponse(
        batch_id=batch_id,
        total=len(jobs),
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        cancelled=cancelled,
        progress=progress,
        jobs=jobs,
    )


@app.post(
    "/api/v1/batches/{batch_id}/cancel",
    response_model=BatchStatusResponse,
)
def cancel_batch(batch_id: str) -> BatchStatusResponse:
    """Revoke queued jobs and mark an unfinished batch as cancelled."""
    manifest = batch_repository.get(batch_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Пакет не найден")

    jobs_to_revoke: list[BatchJob] = []
    for job in manifest.jobs:
        status_response = _job_status(job)
        if status_response.status in {"SUCCESS", "FAILURE", "REVOKED"}:
            continue
        job.cancelled = True
        jobs_to_revoke.append(job)
    if jobs_to_revoke:
        batch_repository.save(manifest)
        for job in jobs_to_revoke:
            try:
                celery_app.control.revoke(job.job_id, terminate=False)
            except Exception:
                logger.warning(
                    "Failed to broadcast revoke for job %s",
                    job.job_id,
                    exc_info=True,
                )
    return get_batch_status(batch_id)


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
)
def get_job_status(job_id: str) -> JobStatusResponse:
    """Return the raw distributed state of one known task."""
    job = _find_job(job_id)
    return _job_status(job)


@app.get("/api/v1/jobs/{job_id}/download")
def download_result(job_id: str) -> StreamingResponse:
    """Stream one completed result from MinIO through the API."""
    job = _find_job(job_id)
    result = _job_status(job)
    if result.status != "SUCCESS" or result.output is None:
        raise HTTPException(status_code=409, detail="Результат ещё не готов")

    try:
        response = storage.open_result(result.output.object_name)
    except Exception as error:
        error_code = getattr(error, "code", None)
        if error_code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(
                status_code=410,
                detail="Результат больше не доступен",
            ) from error
        logger.warning(
            "Failed to open result object %s",
            result.output.object_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Хранилище результатов временно недоступно",
        ) from error
    media_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }
    encoded_filename = quote(result.output.filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }
    return StreamingResponse(
        _stream_and_close(response),
        media_type=media_types[result.output.format],
        headers=headers,
    )


def _find_job(job_id: str) -> BatchJob:
    """Resolve a known task through metadata stored at submission time."""
    job = batch_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


def _job_status(job: BatchJob) -> JobStatusResponse:
    """Map Celery-specific state and metadata to the HTTP contract."""
    if job.cancelled:
        return JobStatusResponse(
            job_id=job.job_id,
            filename=job.filename,
            status="REVOKED",
            progress=100,
            error="Задача отменена пользователем",
        )
    if job.dispatch_error is not None:
        return JobStatusResponse(
            job_id=job.job_id,
            filename=job.filename,
            status="FAILURE",
            progress=100,
            error=job.dispatch_error,
        )

    result = AsyncResult(job.job_id, app=celery_app)
    state = result.state
    worker: str | None = None
    output: OutputDetails | None = None
    error: str | None = None
    progress_by_state = {
        "PENDING": 0,
        "RECEIVED": 5,
        "STARTED": 10,
        "PROCESSING": 50,
        "RETRY": 25,
        "SUCCESS": 100,
        "FAILURE": 100,
        "REVOKED": 100,
    }
    progress = progress_by_state.get(state, 0)

    if state == "SUCCESS" and isinstance(result.result, dict):
        output = OutputDetails.model_validate(result.result)
        worker = output.worker
    elif isinstance(result.info, dict):
        progress = int(result.info.get("progress", progress))
        worker_value = result.info.get("worker")
        worker = str(worker_value) if worker_value is not None else None
    elif state == "FAILURE":
        error = str(result.info)

    return JobStatusResponse(
        job_id=job.job_id,
        filename=job.filename,
        status=state,
        progress=max(0, min(progress, 100)),
        worker=worker,
        output=output,
        error=error,
    )


def _dispatch_jobs(
    manifest: BatchManifest,
    payload: ProcessingOptionsPayload,
) -> int:
    """Dispatch jobs and keep a trackable manifest after a partial failure."""
    serialized_options = payload.model_dump(mode="json")
    for index, job in enumerate(manifest.jobs):
        try:
            process_image_task.apply_async(
                task_id=job.job_id,
                kwargs={
                    "batch_id": manifest.batch_id,
                    "source_object": job.source_object,
                    "source_filename": job.filename,
                    "options": serialized_options,
                },
                retry=True,
                retry_policy={
                    "max_retries": 3,
                    "interval_start": 0,
                    "interval_step": 1,
                    "interval_max": 3,
                },
            )
        except Exception:
            logger.exception(
                "Failed to dispatch job %s from batch %s",
                job.job_id,
                manifest.batch_id,
            )
            message = "Не удалось поставить задачу в очередь"
            for pending_job in manifest.jobs[index:]:
                pending_job.dispatch_error = message
            try:
                batch_repository.save(manifest)
            except Exception:
                logger.exception(
                    "Failed to persist partial dispatch state for batch %s",
                    manifest.batch_id,
                )
            break
    return sum(job.dispatch_error is not None for job in manifest.jobs)


def _delete_sources(object_names: list[str]) -> None:
    """Best-effort cleanup used only before any task has been dispatched."""
    for object_name in object_names:
        try:
            storage.delete_source(object_name)
        except Exception:
            logger.warning(
                "Failed to remove source object %s during rollback",
                object_name,
                exc_info=True,
            )


def _stream_and_close(response: BinaryIO) -> Iterator[bytes]:
    """Release the MinIO HTTP connection after streaming a result."""
    try:
        while chunk := response.read(64 * 1024):
            yield chunk
    finally:
        response.close()
        release_connection = getattr(response, "release_conn", None)
        if release_connection is not None:
            release_connection()
