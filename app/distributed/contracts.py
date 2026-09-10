"""Validated HTTP and queue contracts for distributed processing."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ProcessingOptions
from app.utils.validation import MAX_IMAGE_DIMENSION, MAX_OUTPUT_PIXELS


class ProcessingOptionsPayload(BaseModel):
    """Serializable equivalent of the desktop ProcessingOptions model."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=1, le=MAX_IMAGE_DIMENSION)
    height: int = Field(ge=1, le=MAX_IMAGE_DIMENSION)
    keep_aspect_ratio: bool = True
    output_format: Literal["JPEG", "PNG", "WEBP"] = "JPEG"
    quality: int = Field(default=80, ge=1, le=100)
    rotation: Literal[-90, 0, 90, 180] = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False

    @field_validator("output_format", mode="before")
    @classmethod
    def normalize_output_format(cls, value: object) -> object:
        """Normalize case and the common JPG alias before validation."""
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        return "JPEG" if normalized == "JPG" else normalized

    @model_validator(mode="after")
    def validate_output_pixels(self) -> "ProcessingOptionsPayload":
        """Prevent excessive output memory allocation."""
        if self.width * self.height > MAX_OUTPUT_PIXELS:
            raise ValueError("Результат не должен превышать 100 миллионов пикселей")
        return self

    def to_domain(self) -> ProcessingOptions:
        """Convert the transport model to the existing domain model."""
        return ProcessingOptions(**self.model_dump())


class BatchJob(BaseModel):
    """A single image job recorded as part of a batch."""

    job_id: str
    filename: str
    source_object: str
    dispatch_error: str | None = None
    cancelled: bool = False


class BatchManifest(BaseModel):
    """Persistent list of jobs belonging to a submitted batch."""

    batch_id: str
    jobs: list[BatchJob]


class JobAccepted(BaseModel):
    """Public task identity returned after submission."""

    job_id: str
    filename: str
    queued: bool = True
    error: str | None = None


class BatchCreatedResponse(BaseModel):
    """Response returned after every task dispatch has been attempted."""

    batch_id: str
    total: int
    failed_to_enqueue: int = 0
    jobs: list[JobAccepted]


class OutputDetails(BaseModel):
    """Metadata returned by a successful worker task."""

    object_name: str
    filename: str
    format: str
    width: int
    height: int
    size: int
    worker: str


class JobStatusResponse(BaseModel):
    """Normalized Celery task state exposed to the desktop client."""

    job_id: str
    filename: str
    status: str
    progress: int = Field(ge=0, le=100)
    worker: str | None = None
    output: OutputDetails | None = None
    error: str | None = None


class BatchStatusResponse(BaseModel):
    """Aggregated status of every task in a batch."""

    batch_id: str
    total: int
    pending: int
    processing: int
    completed: int
    failed: int
    cancelled: int = 0
    progress: int = Field(ge=0, le=100)
    jobs: list[JobStatusResponse]


class ClusterWorkerStatus(BaseModel):
    """Live workload reported by one connected Celery worker."""

    worker_id: str
    status: Literal["idle", "busy"]
    active_tasks: int = Field(ge=0)
    active_job_ids: list[str] = Field(default_factory=list)


class ClusterStatusResponse(BaseModel):
    """Observable state of the services participating in processing."""

    api: Literal["online"] = "online"
    redis: Literal["online", "offline"]
    minio: Literal["online", "offline"]
    queue_depth: int | None = Field(default=None, ge=0)
    workers: list[ClusterWorkerStatus] = Field(default_factory=list)
