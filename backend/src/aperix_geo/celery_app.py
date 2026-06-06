"""Celery application instance."""

from pathlib import Path

from celery import Celery
from celery.signals import worker_ready

from aperix_geo.config import get_settings

_BACKEND_DIR = Path(__file__).resolve().parents[2]


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
        beat_schedule_filename=str(_BACKEND_DIR / "celerybeat"),
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


@worker_ready.connect
def _recover_stale_sampling_jobs_on_worker_start(**kwargs) -> None:
    from aperix_geo.tasks.sampling import sampling_recover_stale_jobs

    sampling_recover_stale_jobs.delay(force=True)
