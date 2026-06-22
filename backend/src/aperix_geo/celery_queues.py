"""Celery queue names and task routes for sampling worker pools."""

from __future__ import annotations

from kombu import Exchange, Queue

from aperix_geo.config import Settings

# Default orchestration queue (beat, finalize, continue, brand, alerts).
CELERY_DEFAULT_QUEUE = "aperix"
CELERY_SAMPLING_LLM_QUEUE = "sampling.llm"
CELERY_SAMPLING_CRAWL_QUEUE = "sampling.crawl"
CELERY_SAMPLING_PARSE_QUEUE = "sampling.parse"

_SAMPLING_ORCHESTRATE_TASKS = (
    "aperix_geo.tasks.sampling.sampling_finalize",
    "aperix_geo.tasks.sampling.sampling_orchestrate",
    "aperix_geo.tasks.sampling.sampling_continue",
    "aperix_geo.tasks.sampling.sampling_recover",
    "aperix_geo.tasks.sampling.sampling_tick",
)


def celery_queue_names(*, settings: Settings | None = None) -> tuple[str, str, str, str]:
    from aperix_geo.config import get_settings

    settings = settings or get_settings()
    return (
        settings.celery_default_queue,
        settings.celery_sampling_llm_queue,
        settings.celery_sampling_crawl_queue,
        settings.celery_sampling_parse_queue,
    )


def celery_task_queues(*, settings: Settings | None = None) -> tuple[Queue, ...]:
    default_q, llm_q, crawl_q, parse_q = celery_queue_names(settings=settings)
    exchange = Exchange("aperix", type="direct")
    return (
        Queue(default_q, exchange, routing_key=default_q),
        Queue(llm_q, exchange, routing_key=llm_q),
        Queue(crawl_q, exchange, routing_key=crawl_q),
        Queue(parse_q, exchange, routing_key=parse_q),
    )


def celery_task_routes(*, settings: Settings | None = None) -> dict[str, dict[str, str]]:
    default_q, llm_q, crawl_q, parse_q = celery_queue_names(settings=settings)
    routes = {
        "aperix_geo.tasks.sampling.sampling_llm": {"queue": llm_q},
        "aperix_geo.tasks.sampling.sampling_crawl": {"queue": crawl_q},
        "aperix_geo.tasks.sampling.sampling_parse": {"queue": parse_q},
    }
    routes.update({task: {"queue": default_q} for task in _SAMPLING_ORCHESTRATE_TASKS})
    return routes


def celery_worker_queues_for_role(role: str, *, settings: Settings | None = None) -> str:
    """Comma-separated queue list for ``celery worker -Q``."""
    default_q, llm_q, crawl_q, parse_q = celery_queue_names(settings=settings)
    normalized = (role or "all").strip().lower()
    if normalized == "orch":
        return default_q
    if normalized == "llm":
        return llm_q
    if normalized == "crawl":
        return crawl_q
    if normalized == "parse":
        return parse_q
    return f"{default_q},{llm_q},{crawl_q},{parse_q}"
