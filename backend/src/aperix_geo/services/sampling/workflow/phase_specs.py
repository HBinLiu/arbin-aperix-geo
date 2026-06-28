"""SamplingPhaseSpec builders for Celery llm / crawl / parse tasks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, SamplingJob
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.quota import ai_usage_available
from aperix_geo.services.sampling.cache import (
    clear_cached_llm_result,
    load_prompt_text_cached,
    load_subject_with_competitors_cached,
)
from aperix_geo.services.sampling.llm import SamplingLLMError
from aperix_geo.services.sampling.llm_limits import SamplingRateLimitError
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.retry_policy import is_llm_timeout_error
from aperix_geo.services.sampling.workflow.crawl import crawl_response_citations
from aperix_geo.services.sampling.workflow.execute import (
    chat_result_from_row,
    mark_response_failed,
    mark_response_failed_if_crawl_ready,
    mark_response_failed_if_llm_ready,
    mark_response_failed_if_pending,
    persist_crawl_sample,
    persist_llm_sample,
    persist_parsed_sample,
    prepare_sample_chat_result,
)
from aperix_geo.services.sampling.workflow.phase import SamplingPhaseSpec
from aperix_geo.services.sampling.workflow.phases import phase_expected_status
from aperix_geo.services.sampling.workflow.types import SamplingTaskResult


def _fail_pending(db: Session, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_pending(db, response_id=response_id, error_text=error)
    clear_cached_llm_result(response_id)
    return {"ok": False, "error": error}


def _fail_llm_ready(db: Session, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_llm_ready(db, response_id=response_id, error_text=error)
    return {"ok": False, "error": error}


def _fail_crawl_ready(db: Session, response_id: UUID, error: str) -> SamplingTaskResult:
    mark_response_failed_if_crawl_ready(db, response_id=response_id, error_text=error)
    return {"ok": False, "error": error}


def build_llm_phase_spec(task, response_id: str) -> SamplingPhaseSpec:
    rid = UUID(response_id)
    ctx: dict[str, object] = {"response_id": rid}

    def prepare(db: Session, row: LLMResponse, job: SamplingJob) -> SamplingTaskResult | None:
        prompt_text = load_prompt_text_cached(db, row.prompt_id)
        if not prompt_text:
            mark_response_failed(db, row=row, error_text="missing job or prompt")
            return {"ok": False, "error": "missing prompt"}
        if load_subject_with_competitors_cached(db, job.subject_id) is None:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        if ai_usage_available(db, job.tenant_id) <= 0:
            mark_response_failed(db, row=row, error_text="AI 调用额度已用尽")
            return {"ok": False, "error": "ai quota exceeded", "quota_exhausted": True}
        ctx["platform"] = row.platform
        ctx["prompt_text"] = prompt_text
        ctx["tenant_id"] = job.tenant_id
        ctx["subject_id"] = job.subject_id
        return None

    def work() -> tuple[SamplingChatResult, bool]:
        return prepare_sample_chat_result(
            platform=str(ctx["platform"]),
            prompt_text=str(ctx["prompt_text"]),
            response_id=rid,
            cache=True,
        )

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        if isinstance(exc, SamplingRateLimitError):
            return {"ok": False, "error": str(exc), "rate_limited": True}
        if isinstance(exc, SamplingLLMError):
            mark_response_failed_if_pending(db, response_id=response_id, error_text=str(exc))
            if is_llm_timeout_error(exc):
                clear_cached_llm_result(response_id)
        return {"ok": False, "error": str(exc)}

    return SamplingPhaseSpec(
        phase="llm",
        expected_status=phase_expected_status("llm"),
        prepare=prepare,
        work=work,
        persist=lambda db, response_id, work_result: persist_llm_sample(
            db,
            response_id=response_id,
            chat_result=work_result[0],
            tenant_id=ctx["tenant_id"],  # type: ignore[arg-type]
            subject_id=ctx["subject_id"],  # type: ignore[arg-type]
            live_call=work_result[1],
        ),
        fail=_fail_pending,
        on_skipped=lambda: (clear_cached_llm_result(rid), {"ok": True, "skipped": True, "reason": "no_longer_pending"})[1],
        on_success=lambda: (clear_cached_llm_result(rid), {"ok": True, "phase": "llm"})[1],
        on_work_error=on_work_error,
    )


def build_crawl_phase_spec(_task, _response_id: str) -> SamplingPhaseSpec:
    ctx: dict[str, object] = {}

    def prepare(db: Session, row: LLMResponse, job: SamplingJob) -> SamplingTaskResult | None:
        subject = load_subject_with_competitors_cached(db, job.subject_id)
        if not subject:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        ctx["chat_result"] = chat_result_from_row(row)
        ctx["sampling_job_id"] = row.sampling_job_id
        ctx["subject"] = subject
        return None

    def work() -> None:
        crawl_response_citations(
            chat_result=ctx["chat_result"],
            sampling_job_id=ctx["sampling_job_id"],
            subject=ctx["subject"],
            db=None,
        )

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        mark_response_failed_if_llm_ready(db, response_id=response_id, error_text=str(exc))
        return {"ok": False, "error": str(exc)}

    return SamplingPhaseSpec(
        phase="crawl",
        expected_status=phase_expected_status("crawl"),
        prepare=prepare,
        work=work,
        persist=lambda db, response_id, _work_result: persist_crawl_sample(db, response_id=response_id),
        fail=_fail_llm_ready,
        on_skipped=lambda: {"ok": True, "skipped": True, "reason": "no_longer_llm_ready"},
        on_success=lambda: {"ok": True, "phase": "crawl"},
        on_work_error=on_work_error,
    )


def build_parse_phase_spec(_task, response_id: str) -> SamplingPhaseSpec:
    rid = UUID(response_id)
    ctx: dict[str, object] = {}

    def prepare(db: Session, row: LLMResponse, job: SamplingJob) -> SamplingTaskResult | None:
        subject = load_subject_with_competitors_cached(db, job.subject_id)
        if not subject:
            mark_response_failed(db, row=row, error_text="missing subject")
            return {"ok": False, "error": "missing subject"}
        ctx["chat_result"] = chat_result_from_row(row)
        ctx["subject"] = subject
        ctx["sampling_job_id"] = row.sampling_job_id
        ctx["tenant_id"] = job.tenant_id
        return None

    def work():
        chat_result = ctx["chat_result"]
        subject = ctx["subject"]
        parsed = parse_llm_output(
            chat_result.text,
            subject=subject,
            source_urls=list(chat_result.source_urls),
            web_search_mode=chat_result.web_search_mode,
            sampling_job_id=ctx["sampling_job_id"],
            db=None,
            fetch_pages=False,
        )
        return chat_result, parsed

    def persist(db: Session, response_id: UUID, work_result) -> bool:
        chat_result, parsed = work_result
        return persist_parsed_sample(
            db,
            response_id=response_id,
            subject=ctx["subject"],  # type: ignore[arg-type]
            chat_result=chat_result,
            parsed=parsed,
            tenant_id=ctx["tenant_id"],  # type: ignore[arg-type]
            absa_live_call=parsed.absa_live_call,
        )

    def on_success() -> SamplingTaskResult:
        from aperix_geo.services.brand.backfill import maybe_enqueue_brand_domain_backfill

        maybe_enqueue_brand_domain_backfill(rid)
        return {"ok": True, "phase": "parse"}

    def on_work_error(db: Session, response_id: UUID, exc: BaseException) -> SamplingTaskResult:
        mark_response_failed_if_crawl_ready(db, response_id=response_id, error_text=str(exc))
        return {"ok": False, "error": str(exc)}

    return SamplingPhaseSpec(
        phase="parse",
        expected_status=phase_expected_status("parse"),
        prepare=prepare,
        work=work,
        persist=persist,
        fail=_fail_crawl_ready,
        on_skipped=lambda: {"ok": True, "skipped": True, "reason": "no_longer_crawl_ready"},
        on_success=on_success,
        on_work_error=on_work_error,
    )
