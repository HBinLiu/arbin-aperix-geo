"""Worker phase constants shared by fill, Celery tasks, and status derivation.

Phases:
  - llm: produce chat sample (dispatches to api or account-crawl Celery task)
  - page: fetch citation source pages (former phase name ``crawl``)
  - parse: ABSA + citation merge
"""

from __future__ import annotations

from aperix_geo.db.models import LLMResponseStatus

SAMPLING_PHASES = ("llm", "page", "parse")

# Legacy alias used by older call sites / Redis keys during transition.
PHASE_PAGE_ALIASES = frozenset({"page", "crawl"})

PHASE_EXPECTED_STATUS: dict[str, LLMResponseStatus] = {
    "llm": LLMResponseStatus.pending,
    "page": LLMResponseStatus.llm_ready,
    "parse": LLMResponseStatus.crawl_ready,
}

NEXT_FILL_PHASE: dict[str, str] = {
    "llm": "page",
    "page": "parse",
}

PHASE_CELERY_TASKS: dict[str, str] = {
    "llm": "aperix_geo.tasks.sampling.sampling_llm",  # overridden per-backend in fill
    "page": "aperix_geo.tasks.sampling.sampling_page",
    "parse": "aperix_geo.tasks.sampling.sampling_parse",
}

SAMPLING_LLM_API_TASK = "aperix_geo.tasks.sampling.sampling_llm"
SAMPLING_LLM_CRAWL_TASK = "aperix_geo.tasks.sampling.sampling_crawl"
SAMPLING_DISPATCH = "aperix_geo.tasks.sampling.sampling_dispatch"


def normalize_sampling_phase(phase: str) -> str:
    raw = (phase or "").strip().lower()
    if raw == "crawl":
        return "page"
    return raw


def phase_celery_task(phase: str) -> str:
    key = normalize_sampling_phase(phase)
    try:
        return PHASE_CELERY_TASKS[key]
    except KeyError as exc:
        raise ValueError(f"invalid sampling phase: {phase}") from exc


def phase_expected_status(phase: str) -> LLMResponseStatus:
    key = normalize_sampling_phase(phase)
    try:
        return PHASE_EXPECTED_STATUS[key]
    except KeyError as exc:
        raise ValueError(f"invalid sampling phase: {phase}") from exc


def is_sampling_phase(phase: str) -> bool:
    return normalize_sampling_phase(phase) in PHASE_EXPECTED_STATUS
