"""Celery tasks executed by independent Pixora worker nodes."""

import logging
from pathlib import Path

from celery.exceptions import Ignore
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)
from urllib3.exceptions import HTTPError as HttpTransportError

from app.distributed.celery_app import celery_app, settings
from app.distributed.contracts import ProcessingOptionsPayload
from app.distributed.repository import BatchRepository
from app.distributed.storage import ObjectStorage
from app.services import ImageService


FORMAT_DETAILS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}
logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="pixora.process_image",
    autoretry_for=(
        HttpTransportError,
        ConnectionError,
        TimeoutError,
        RedisConnectionError,
        RedisTimeoutError,
    ),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)
def process_image_task(
    self,
    *,
    batch_id: str,
    source_object: str,
    source_filename: str,
    options: dict[str, object],
) -> dict[str, object]:
    """Download, process and upload one independently scheduled image."""
    worker_name = self.request.hostname or "unknown-worker"
    self.update_state(
        state="PROCESSING",
        meta={"progress": 10, "worker": worker_name},
    )

    payload = ProcessingOptionsPayload.model_validate(options)
    domain_options = payload.to_domain()
    storage = ObjectStorage(settings)
    job_id = str(self.request.id) if self.request.id is not None else None
    if _job_cancelled(job_id):
        _delete_source_best_effort(storage, source_object)
        raise Ignore()
    source_data = storage.get_source(source_object)

    self.update_state(
        state="PROCESSING",
        meta={"progress": 35, "worker": worker_name},
    )
    service = ImageService()
    result = service.process_bytes(
        source_data,
        domain_options,
        filename=source_filename,
        fit_within_bounds=True,
    )
    try:
        encoded_data = service.encode(result, domain_options)
        output_format = payload.output_format
        extension, content_type = FORMAT_DETAILS[output_format]
        output_filename = f"{Path(source_filename).stem}_pixora{extension}"
        output_object = f"{batch_id}/{self.request.id}/{output_filename}"

        self.update_state(
            state="PROCESSING",
            meta={"progress": 80, "worker": worker_name},
        )
        if _job_cancelled(job_id):
            _delete_source_best_effort(storage, source_object)
            raise Ignore()
        storage.put_result(
            output_object,
            encoded_data,
            content_type,
        )
        _delete_source_best_effort(storage, source_object)
        return {
            "object_name": output_object,
            "filename": output_filename,
            "format": output_format,
            "width": result.width,
            "height": result.height,
            "size": len(encoded_data),
            "worker": worker_name,
        }
    finally:
        result.close()


def _job_cancelled(job_id: str | None) -> bool:
    """Read the durable cancellation flag before expensive worker steps."""
    if job_id is None:
        return False
    job = BatchRepository(settings).get_job(job_id)
    return bool(job is not None and job.cancelled)


def _delete_source_best_effort(
    storage: ObjectStorage,
    source_object: str,
) -> None:
    """Remove input data without turning successful processing into a failure."""
    try:
        storage.delete_source(source_object)
    except Exception:
        logger.warning(
            "Failed to remove source object %s",
            source_object,
            exc_info=True,
        )
