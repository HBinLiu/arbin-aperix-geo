"""Worker phase constants shared by fill, Celery tasks, and status derivation."""

from __future__ import annotations

from aperix_geo.db.models import LLMResponseStatus

SAMPLING_PHASES = ("llm", "crawl", "parse")

PHASE_EXPECTED_STATUS: dict[str, LLMResponseStatus] = {
    "llm": LLMResponseStatus.pending,
    "crawl": LLMResponseStatus.llm_ready,
    "parse": LLMResponseStatus.crawl_ready,
}

NEXT_FILL_PHASE: dict[str, str] = {
    "llm": "crawl",
    "crawl": "parse",
}

PHASE_CELERY_TASKS: dict[str, str] = {
    "llm": "aperix_geo.tasks.sampling.sampling_llm",
    "crawl": "aperix_geo.tasks.sampling.sampling_crawl",
    "parse": "aperix_geo.tasks.sampling.sampling_parse",
}

SAMPLING_DISPATCH = "aperix_geo.tasks.sampling.sampling_dispatch"


def phase_celery_task(phase: str) -> str:
    try:
        return PHASE_CELERY_TASKS[phase]
    except KeyError as exc:
        raise ValueError(f"invalid sampling phase: {phase}") from exc


def phase_expected_status(phase: str) -> LLMResponseStatus:
    try:
        return PHASE_EXPECTED_STATUS[phase]
    except KeyError as exc:
        raise ValueError(f"invalid sampling phase: {phase}") from exc


def is_sampling_phase(phase: str) -> bool:
    return phase in PHASE_EXPECTED_STATUS
