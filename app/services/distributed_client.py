"""HTTP client used by the desktop app to reach the Pixora coordinator."""

import json
import mimetypes
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from app.models import ProcessingOptions
from app.utils.validation import (
    DEFAULT_MAX_BATCH_FILES,
    DEFAULT_MAX_BATCH_SIZE_BYTES,
    validate_image_file,
)


class DistributedApiError(RuntimeError):
    """Raised when the remote processing coordinator cannot fulfil a request."""


class DistributedClient:
    """Keep the desktop application independent from infrastructure libraries."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout_seconds: float = 30.0,
        max_batch_files: int = DEFAULT_MAX_BATCH_FILES,
        max_batch_size_bytes: int = DEFAULT_MAX_BATCH_SIZE_BYTES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_batch_files = max_batch_files
        self.max_batch_size_bytes = max_batch_size_bytes

    def check_health(self) -> bool:
        """Return True when the distributed API and its dependencies are ready."""
        response = self._request_json("GET", "/health")
        return response.get("status") == "ok"

    def submit_batch(
        self,
        image_paths: list[str | Path],
        options: ProcessingOptions,
    ) -> dict[str, Any]:
        """Upload multiple source files and return their batch identity."""
        if not image_paths:
            raise ValueError("Не выбраны изображения для пакетной обработки")
        if len(image_paths) > self.max_batch_files:
            raise ValueError(
                f"В одном пакете допускается не более {self.max_batch_files} файлов"
            )

        validated_paths = [validate_image_file(path) for path in image_paths]
        total_size = sum(path.stat().st_size for path in validated_paths)
        if total_size > self.max_batch_size_bytes:
            raise ValueError("Суммарный размер пакета превышает допустимый предел")
        body, content_type = self._build_multipart(validated_paths, options)
        return self._request_json(
            "POST",
            "/api/v1/batches",
            data=body,
            headers={"Content-Type": content_type},
        )

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """Fetch aggregate and per-image processing progress."""
        return self._request_json(
            "GET",
            f"/api/v1/batches/{quote(batch_id, safe='')}",
        )

    def cancel_batch(self, batch_id: str) -> dict[str, Any]:
        """Request cancellation of every unfinished task in a batch."""
        return self._request_json(
            "POST",
            f"/api/v1/batches/{quote(batch_id, safe='')}/cancel",
            data=b"",
        )

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Fetch processing state for one image task."""
        return self._request_json(
            "GET",
            f"/api/v1/jobs/{quote(job_id, safe='')}",
        )

    def download_result(
        self,
        job_id: str,
        destination: str | Path,
    ) -> Path:
        """Download one completed output atomically to a local path."""
        destination_path = Path(destination)
        temporary_path = destination_path.with_name(
            f".{destination_path.name}.{uuid4().hex}.part"
        )
        request = Request(
            self._url(f"/api/v1/jobs/{quote(job_id, safe='')}/download"),
            method="GET",
        )
        try:
            with self._open(request) as response, temporary_path.open("wb") as file:
                while chunk := response.read(64 * 1024):
                    file.write(chunk)
            temporary_path.replace(destination_path)
        except (HTTPError, URLError, OSError) as error:
            temporary_path.unlink(missing_ok=True)
            raise self._translate_error(error) from error
        return destination_path

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = Request(
            self._url(path),
            data=data,
            headers=headers or {},
            method=method,
        )
        try:
            with self._open(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError) as error:
            raise self._translate_error(error) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DistributedApiError("API Pixora вернуло некорректный ответ") from error
        if not isinstance(payload, dict):
            raise DistributedApiError("API Pixora вернуло некорректный ответ")
        return payload

    def _open(self, request: Request):
        """Open one request; kept separate to make network tests deterministic."""
        return urlopen(request, timeout=self.timeout_seconds)

    def _build_multipart(
        self,
        paths: list[Path],
        options: ProcessingOptions,
    ) -> tuple[bytes, str]:
        boundary = f"pixora-{uuid4().hex}"
        body = bytearray()

        def append_line(value: str = "") -> None:
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")

        append_line(f"--{boundary}")
        append_line('Content-Disposition: form-data; name="options"')
        append_line("Content-Type: application/json; charset=utf-8")
        append_line()
        append_line(
            json.dumps(
                asdict(options),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

        for path in paths:
            filename = path.name.replace('"', "_")
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            append_line(f"--{boundary}")
            append_line(
                'Content-Disposition: form-data; name="files"; '
                f'filename="{filename}"'
            )
            append_line(f"Content-Type: {content_type}")
            append_line()
            body.extend(path.read_bytes())
            body.extend(b"\r\n")

        append_line(f"--{boundary}--")
        return bytes(body), f"multipart/form-data; boundary={boundary}"

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _translate_error(error: Exception) -> DistributedApiError:
        """Turn low-level urllib exceptions into readable application errors."""
        if isinstance(error, HTTPError):
            detail = error.reason
            try:
                payload = json.loads(error.read().decode("utf-8"))
                detail = payload.get("detail", detail)
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
            return DistributedApiError(
                f"API Pixora вернуло ошибку {error.code}: {detail}"
            )
        if isinstance(error, URLError):
            return DistributedApiError(
                f"Не удалось подключиться к API Pixora: {error.reason}"
            )
        return DistributedApiError(f"Ошибка обмена с API Pixora: {error}")
