"""Tests for the desktop HTTP client without a running server."""

import json
from io import BytesIO
from urllib.error import URLError

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.services import DistributedApiError, DistributedClient


class FakeResponse:
    """Minimal context-managed urllib response."""

    def __init__(self, data: bytes) -> None:
        self.buffer = BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.buffer.close()

    def read(self, size: int = -1) -> bytes:
        return self.buffer.read(size)


def test_client_builds_batch_request(monkeypatch, tmp_path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (4, 3), "red").save(first)
    Image.new("RGB", (4, 3), "blue").save(second)
    captured = {}
    response_data = {
        "batch_id": "batch-1",
        "total": 2,
        "jobs": [],
    }

    client = DistributedClient()

    def fake_open(request):
        captured["request"] = request
        return FakeResponse(json.dumps(response_data).encode())

    monkeypatch.setattr(client, "_open", fake_open)

    response = client.submit_batch(
        [first, second],
        ProcessingOptions(320, 200, output_format="WEBP", quality=70),
    )

    request = captured["request"]
    assert response["batch_id"] == "batch-1"
    assert request.full_url.endswith("/api/v1/batches")
    assert request.method == "POST"
    assert request.data.count(b'name="files"') == 2
    assert b'"output_format":"WEBP"' in request.data


def test_client_reports_connection_error(monkeypatch) -> None:
    client = DistributedClient()
    monkeypatch.setattr(
        client,
        "_open",
        lambda _request: (_ for _ in ()).throw(URLError("offline")),
    )

    with pytest.raises(DistributedApiError, match="подключиться"):
        client.check_health()


def test_client_requests_batch_cancellation(monkeypatch) -> None:
    client = DistributedClient()
    captured = {}

    def fake_open(request):
        captured["request"] = request
        return FakeResponse(b'{"batch_id":"batch-1","jobs":[]}')

    monkeypatch.setattr(client, "_open", fake_open)

    client.cancel_batch("batch-1")

    request = captured["request"]
    assert request.method == "POST"
    assert request.full_url.endswith("/api/v1/batches/batch-1/cancel")


def test_client_rejects_batch_before_building_an_oversized_request(
    monkeypatch,
) -> None:
    client = DistributedClient(max_batch_files=1)
    monkeypatch.setattr(
        "app.services.distributed_client.validate_image_file",
        lambda path: path,
    )

    with pytest.raises(ValueError, match="не более 1"):
        client.submit_batch(
            ["first.png", "second.png"],
            ProcessingOptions(10, 10),
        )


def test_client_downloads_result_atomically(monkeypatch, tmp_path) -> None:
    client = DistributedClient()
    monkeypatch.setattr(
        client,
        "_open",
        lambda _request: FakeResponse(b"encoded-image"),
    )
    destination = tmp_path / "result.webp"

    saved_path = client.download_result("job-1", destination)

    assert saved_path == destination
    assert destination.read_bytes() == b"encoded-image"
    assert list(tmp_path.glob("*.part")) == []
