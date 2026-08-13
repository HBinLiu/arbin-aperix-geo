"""Celery application instance."""

import os
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_ready

from aperix_geo.celery_queues import (
    celery_task_queues,
    celery_task_routes,
)
from aperix_geo.config import get_settings
from aperix_geo.services.sampling.workflow.schedule import (
    SAMPLING_TIMEZONE,
    sampling_beat_cron_hour_range,
)

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def make_celery() -> Celery:
    s = get_settings()
    app = Celery(
        "aperix_geo",
        broker=s.celery_broker_url,
        backend=s.celery_result_backend,
    )
    redis_transport = {
        "socket_timeout": s.celery_redis_socket_timeout_s,
        "socket_connect_timeout": s.celery_redis_connect_timeout_s,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    }
    interval = s.sampling_scheduler_interval_minutes
    beat_hours = sampling_beat_cron_hour_range(settings=s)
    hb_interval = max(5, int(s.doubao_heartbeat_interval_min))
    app.conf.update(
        task_default_queue=s.celery_default_queue,
        task_queues=celery_task_queues(settings=s),
        task_routes=celery_task_routes(settings=s),
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone=SAMPLING_TIMEZONE,
        enable_utc=True,
        result_backend_transport_options=redis_transport,
        broker_transport_options=redis_transport,
        beat_schedule_filename=str(_BACKEND_DIR / "celerybeat"),
        beat_schedule={
            # 仅在每日采样窗口内 tick；窗口内各 subject 按 id hash 到不同 minute slot
            "sampling-scheduler-tick": {
                "task": "aperix_geo.tasks.sampling.sampling_tick",
                "schedule": crontab(minute=f"*/{interval}", hour=beat_hours),
            },
            "billing-maintenance": {
                "task": "aperix_geo.tasks.billing.billing_maintenance",
                "schedule": crontab(minute=5, hour=0),
            },
            # Task no-ops when DOUBAO_HEARTBEAT_ENABLED=false
            "crawl-account-heartbeat": {
                "task": "aperix_geo.tasks.crawl_accounts.crawl_account_heartbeat",
                "schedule": crontab(minute=f"*/{hb_interval}"),
            },
        },
    )
    app.conf.include = [
        "aperix_geo.tasks.sampling",
        "aperix_geo.tasks.brand",
        "aperix_geo.tasks.domain",
        "aperix_geo.tasks.alert",
        "aperix_geo.tasks.billing",
        "aperix_geo.tasks.knowledge",
        "aperix_geo.tasks.crawl_accounts",
        "aperix_geo.tasks.setup",
    ]
    return app


celery_app = make_celery()

from aperix_geo.utils.logging import configure  # noqa: E402

configure()


def _recover_stale_sampling_jobs_on_worker_start(**kwargs) -> None:
    """Run stale-job recovery once from the orchestration worker pool."""
    role = os.environ.get("CELERY_WORKER_ROLE", "all").strip().lower()
    if role not in ("all", "orch"):
        return
    from aperix_geo.tasks.sampling import sampling_recover

    sampling_recover.delay(force=True)


worker_ready.connect(_recover_stale_sampling_jobs_on_worker_start)


def _warmup_http_on_worker_process(**kwargs) -> None:
    from aperix_geo.services.crawl._httpx import warmup_http_stack

    warmup_http_stack()
    # Doubao sampling + heartbeat run in geo-web-crawl (HTTP / cli) — no
    # in-process Sync Playwright warmup needed here.


worker_process_init.connect(_warmup_http_on_worker_process)
