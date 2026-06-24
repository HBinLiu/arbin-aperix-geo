"""Tests for Celery queue routing."""

from aperix_geo.celery_queues import (
    CELERY_DEFAULT_QUEUE,
    CELERY_SAMPLING_CRAWL_QUEUE,
    CELERY_SAMPLING_LLM_QUEUE,
    CELERY_SAMPLING_PARSE_QUEUE,
    celery_task_routes,
    celery_worker_queues_for_role,
)
from aperix_geo.config import Settings


def test_celery_task_routes_split_sampling_tasks() -> None:
    routes = celery_task_routes(
        settings=Settings(
            celery_default_queue=CELERY_DEFAULT_QUEUE,
            celery_sampling_llm_queue=CELERY_SAMPLING_LLM_QUEUE,
            celery_sampling_crawl_queue=CELERY_SAMPLING_CRAWL_QUEUE,
            celery_sampling_parse_queue=CELERY_SAMPLING_PARSE_QUEUE,
        )
    )
    assert routes["aperix_geo.tasks.sampling.sampling_llm"]["queue"] == CELERY_SAMPLING_LLM_QUEUE
    assert routes["aperix_geo.tasks.sampling.sampling_crawl"]["queue"] == CELERY_SAMPLING_CRAWL_QUEUE
    assert routes["aperix_geo.tasks.sampling.sampling_parse"]["queue"] == CELERY_SAMPLING_PARSE_QUEUE
    assert routes["aperix_geo.tasks.sampling.sampling_dispatch"]["queue"] == CELERY_DEFAULT_QUEUE


def test_celery_worker_queues_for_role() -> None:
    settings = Settings(
        celery_default_queue="aperix",
        celery_sampling_llm_queue="sampling.llm",
        celery_sampling_crawl_queue="sampling.crawl",
        celery_sampling_parse_queue="sampling.parse",
    )
    assert celery_worker_queues_for_role("orch", settings=settings) == "aperix"
    assert celery_worker_queues_for_role("llm", settings=settings) == "sampling.llm"
    assert celery_worker_queues_for_role("crawl", settings=settings) == "sampling.crawl"
    assert celery_worker_queues_for_role("parse", settings=settings) == "sampling.parse"
    assert (
        celery_worker_queues_for_role("all", settings=settings)
        == "aperix,sampling.llm,sampling.crawl,sampling.parse"
    )
