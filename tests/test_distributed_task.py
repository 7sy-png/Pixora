"""Tests for the independently executable Celery image task."""

from io import BytesIO

from PIL import Image
from celery.exceptions import Ignore
import pytest

import app.distributed.tasks as task_module


class RecordingStorage:
    """In-memory replacement for MinIO used by the worker test."""

    source_data = b""
    uploaded: tuple[str, bytes, str] | None = None
    deleted: str | None = None

    def __init__(self, _settings) -> None:
        pass

    def get_source(self, _object_name: str) -> bytes:
        return self.source_data

    def put_result(
        self,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        type(self).uploaded = (object_name, data, content_type)

    def delete_source(self, object_name: str) -> None:
        type(self).deleted = object_name


def test_celery_task_reuses_image_service_and_uploads_result(monkeypatch) -> None:
    source = BytesIO()
    Image.new("RGB", (12, 8), "purple").save(source, format="PNG")
    RecordingStorage.source_data = source.getvalue()
    RecordingStorage.uploaded = None
    RecordingStorage.deleted = None

    monkeypatch.setattr(task_module, "ObjectStorage", RecordingStorage)
    monkeypatch.setattr(
        task_module.process_image_task,
        "update_state",
        lambda **_kwargs: None,
    )

    task_result = task_module.process_image_task.run(
        batch_id="batch-1",
        source_object="batch-1/job-1/source.png",
        source_filename="source.png",
        options={
            "width": 6,
            "height": 4,
            "output_format": "WEBP",
            "quality": 75,
        },
    )

    assert task_result["filename"] == "source_pixora.webp"
    assert task_result["format"] == "WEBP"
    assert task_result["width"] == 6
    assert task_result["height"] == 4
    assert RecordingStorage.uploaded is not None
    assert RecordingStorage.deleted == "batch-1/job-1/source.png"
    _, encoded, content_type = RecordingStorage.uploaded
    assert content_type == "image/webp"
    with Image.open(BytesIO(encoded)) as image:
        assert image.format == "WEBP"
        assert image.size == (6, 4)


def test_celery_task_discards_a_durably_cancelled_job(monkeypatch) -> None:
    RecordingStorage.uploaded = None
    RecordingStorage.deleted = None
    monkeypatch.setattr(task_module, "ObjectStorage", RecordingStorage)
    monkeypatch.setattr(task_module, "_job_cancelled", lambda _job_id: True)
    monkeypatch.setattr(
        task_module.process_image_task,
        "update_state",
        lambda **_kwargs: None,
    )

    with pytest.raises(Ignore):
        task_module.process_image_task.run(
            batch_id="batch-1",
            source_object="batch-1/job-1/source.png",
            source_filename="source.png",
            options={
                "width": 6,
                "height": 4,
                "output_format": "WEBP",
            },
        )

    assert RecordingStorage.uploaded is None
    assert RecordingStorage.deleted == "batch-1/job-1/source.png"
