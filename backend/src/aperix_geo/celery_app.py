"""Celery application instance."""

from celery import Celery

from aperix_geo.config import get_settings


def make_celery() -> Celery:
    s = get_settings()
    app = Celery(
        "aperix_geo",
        broker=s.celery_broker_url,
        backend=s.celery_result_backend,
    )
    tick = s.sampling_scheduler_tick_seconds
    app.conf.update(
        task_default_queue="aperix",
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "sampling-scheduler-tick": {
                "task": "aperix_geo.tasks.sampling.sampling_scheduled_tick",
                "schedule": tick,
            },
        },
    )
    app.conf.include = ["aperix_geo.tasks.sampling"]
    return app


celery_app = make_celery()
