"""Environment-based configuration for distributed Pixora services."""

from dataclasses import dataclass
from os import getenv

from app.utils.validation import (
    DEFAULT_MAX_BATCH_FILES,
    DEFAULT_MAX_BATCH_SIZE_BYTES,
)


def _get_int(name: str, default: int) -> int:
    """Read a positive integer setting from the environment."""
    raw_value = getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} должно быть целым числом") from error
    if value < 1:
        raise ValueError(f"{name} должно быть больше нуля")
    return value


def _get_bool(name: str, default: bool) -> bool:
    """Read a conventional boolean setting from the environment."""
    raw_value = getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} должно содержать true или false")


@dataclass(frozen=True, slots=True)
class DistributedSettings:
    """Connection details shared by the API and worker containers."""

    redis_broker_url: str
    redis_result_url: str
    redis_metadata_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool
    minio_input_bucket: str
    minio_result_bucket: str
    max_batch_files: int
    max_batch_size_bytes: int
    result_expires_seconds: int


def load_settings() -> DistributedSettings:
    """Build distributed settings without coupling to a framework."""
    return DistributedSettings(
        redis_broker_url=getenv(
            "PIXORA_REDIS_BROKER_URL", "redis://localhost:6379/0"
        ),
        redis_result_url=getenv(
            "PIXORA_REDIS_RESULT_URL", "redis://localhost:6379/1"
        ),
        redis_metadata_url=getenv(
            "PIXORA_REDIS_METADATA_URL", "redis://localhost:6379/2"
        ),
        minio_endpoint=getenv("PIXORA_MINIO_ENDPOINT", "localhost:9000"),
        minio_access_key=getenv("PIXORA_MINIO_ACCESS_KEY", "pixora"),
        minio_secret_key=getenv(
            "PIXORA_MINIO_SECRET_KEY", "pixora-development"
        ),
        minio_secure=_get_bool("PIXORA_MINIO_SECURE", False),
        minio_input_bucket=getenv(
            "PIXORA_MINIO_INPUT_BUCKET", "pixora-input"
        ),
        minio_result_bucket=getenv(
            "PIXORA_MINIO_RESULT_BUCKET", "pixora-results"
        ),
        max_batch_files=_get_int(
            "PIXORA_MAX_BATCH_FILES",
            DEFAULT_MAX_BATCH_FILES,
        ),
        max_batch_size_bytes=_get_int(
            "PIXORA_MAX_BATCH_SIZE_BYTES",
            DEFAULT_MAX_BATCH_SIZE_BYTES,
        ),
        result_expires_seconds=_get_int(
            "PIXORA_RESULT_EXPIRES_SECONDS", 24 * 60 * 60
        ),
    )
