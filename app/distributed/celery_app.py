"""Celery application configured for Redis transport and result storage."""

from celery import Celery

from app.distributed.config import load_settings


settings = load_settings()

celery_app = Celery(
    "pixora",
    broker=settings.redis_broker_url,
    backend=settings.redis_result_url,
    include=("app.distributed.tasks",),
)
celery_app.conf.update(
    accept_content=("json",),
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=settings.result_expires_seconds,
    task_time_limit=300,
)
