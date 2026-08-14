"""Celery queue names and task routes for sampling worker pools.

Lanes:
  - api   (sampling.api): HTTP provider sampling (alias sampling.llm)
  - crawl (sampling.crawl): account-pool browser platform sampling
  - page  (sampling.page): citation page fetch (former sampling.crawl meaning)
  - parse (sampling.parse): ABSA / merge
"""

from __future__ import annotations

from kombu import Exchange, Queue

from aperix_geo.config import Settings

# Default orchestration queue (beat, finalize, continue, brand, alerts).
CELERY_DEFAULT_QUEUE = "aperix"
CELERY_SAMPLING_API_QUEUE = "sampling.api"
CELERY_SAMPLING_LLM_QUEUE = CELERY_SAMPLING_API_QUEUE  # backward-compatible alias
CELERY_SAMPLING_CRAWL_QUEUE = "sampling.crawl"  # account-pool platforms
CELERY_SAMPLING_PAGE_QUEUE = "sampling.page"  # citation pages
CELERY_SAMPLING_PARSE_QUEUE = "sampling.parse"

_SAMPLING_ORCHESTRATE_TASKS = (
    "aperix_geo.tasks.sampling.sampling_dispatch",
    "aperix_geo.tasks.sampling.sampling_orchestrate",
    "aperix_geo.tasks.sampling.sampling_continue",
    "aperix_geo.tasks.sampling.sampling_recover",
    "aperix_geo.tasks.sampling.sampling_tick",
    "aperix_geo.tasks.sampling.sampling_fill",
    "aperix_geo.tasks.sampling.sampling_finalize",
    "aperix_geo.tasks.sampling.sampling_reconcile",
)


def celery_queue_names(*, settings: Settings | None = None) -> tuple[str, str, str, str, str]:
    from aperix_geo.config import get_settings

    settings = settings or get_settings()
    return (
        settings.celery_default_queue,
        settings.celery_sampling_api_queue,
        settings.celery_sampling_crawl_queue,
        settings.celery_sampling_page_queue,
        settings.celery_sampling_parse_queue,
    )


def celery_task_queues(*, settings: Settings | None = None) -> tuple[Queue, ...]:
    default_q, api_q, crawl_q, page_q, parse_q = celery_queue_names(settings=settings)
    exchange = Exchange("aperix", type="direct")
    declared = [default_q, api_q, crawl_q, page_q, parse_q]
    # Keep legacy sampling.llm declared when api queue was renamed away from it.
    if "sampling.llm" not in declared and api_q != "sampling.llm":
        declared.append("sampling.llm")
    return tuple(Queue(name, exchange, routing_key=name) for name in declared)


def celery_task_routes(*, settings: Settings | None = None) -> dict[str, dict[str, str]]:
    default_q, api_q, crawl_q, page_q, parse_q = celery_queue_names(settings=settings)
    routes = {
        "aperix_geo.tasks.sampling.sampling_llm": {"queue": api_q},
        "aperix_geo.tasks.sampling.sampling_api": {"queue": api_q},
        "aperix_geo.tasks.sampling.sampling_crawl": {"queue": crawl_q},
        "aperix_geo.tasks.sampling.sampling_page": {"queue": page_q},
        "aperix_geo.tasks.sampling.sampling_parse": {"queue": parse_q},
    }
    routes.update({task: {"queue": default_q} for task in _SAMPLING_ORCHESTRATE_TASKS})
    return routes


def celery_worker_queues_for_role(role: str, *, settings: Settings | None = None) -> str:
    """Comma-separated queue list for ``celery worker -Q``."""
    default_q, api_q, crawl_q, page_q, parse_q = celery_queue_names(settings=settings)
    normalized = (role or "all").strip().lower()
    if normalized == "orch":
        return default_q
    if normalized in ("api", "llm"):  # llm = legacy alias for api
        return api_q
    if normalized == "crawl":
        return crawl_q
    if normalized == "page":
        return page_q
    if normalized == "parse":
        return parse_q
    return f"{default_q},{api_q},{crawl_q},{page_q},{parse_q}"
