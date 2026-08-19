"""Fill sampling phases up to the in-flight cap."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from aperix_geo.config import get_settings
from aperix_geo.db.models import LLMResponse, LLMResponseStatus
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.claim import response_claim_active
from aperix_geo.services.sampling.workflow.finalize import schedule_job_finalize
from aperix_geo.services.sampling.workflow.logging import log_sampling
from aperix_geo.services.sampling.workflow.phases import (
    NEXT_FILL_PHASE,
    SAMPLING_LLM_API_TASK,
    SAMPLING_LLM_CRAWL_TASK,
    SAMPLING_PHASES,
    is_sampling_phase,
    normalize_sampling_phase,
    phase_expected_status,
)
from aperix_geo.utils.cache.redis_kv import redis_delete, redis_set_nx_strict, shared_redis_client

SAMPLING_FILL = "aperix_geo.tasks.sampling.sampling_fill"

_ACQUIRE_INFLIGHT_SCRIPT = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local max = tonumber(ARGV[1])
if current >= max then return 0 end
local new = redis.call('INCR', KEYS[1])
redis.call('EXPIRE', KEYS[1], ARGV[2])
if new > max then
  redis.call('DECR', KEYS[1])
  return 0
end
return 1
"""


def _inflight_key(job_id: UUID, phase: str, *, lane: str = "") -> str:
    phase = normalize_sampling_phase(phase)
    if phase == "llm" and lane:
        return f"aperix:sampling:inflight:{job_id}:{phase}:{lane}"
    return f"aperix:sampling:inflight:{job_id}:{phase}"


def _dispatch_key(phase: str, response_id: UUID) -> str:
    return f"aperix:sampling:dispatch:{normalize_sampling_phase(phase)}:{response_id}"


def _dispatch_index_key(job_id: UUID, phase: str) -> str:
    return f"aperix:sampling:dispatch_index:{job_id}:{normalize_sampling_phase(phase)}"


def _inflight_ttl_s(*, phase: str = "", lane: str = "") -> int:
    """Longer TTL for crawl lane: tasks may sit in broker for a long time."""
    settings = get_settings()
    base = min(3600, max(600, settings.sampling_stale_job_seconds * 20))
    if normalize_sampling_phase(phase) == "llm" and lane == "crawl":
        # Up to 6h — single-account daily backlog.
        return max(base, min(6 * 3600, int(settings.doubao_crawl_timeout_s) * 120))
    return base


def try_reserve_inflight_slot(
    job_id: UUID,
    phase: str,
    max_slots: int,
    *,
    lane: str = "",
) -> bool:
    phase = normalize_sampling_phase(phase)
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return True
    key = _inflight_key(job_id, phase, lane=lane)
    ttl = _inflight_ttl_s(phase=phase, lane=lane)
    try:
        result = client.eval(_ACQUIRE_INFLIGHT_SCRIPT, 1, key, max_slots, ttl)
        return int(result) == 1
    except Exception:
        log_sampling(logging.WARNING, "采样 inflight 预留失败", phase=phase, job_id=job_id)
        return True


def release_inflight_slot(job_id: UUID, phase: str, *, lane: str = "") -> None:
    phase = normalize_sampling_phase(phase)
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return
    key = _inflight_key(job_id, phase, lane=lane)
    ttl = _inflight_ttl_s(phase=phase, lane=lane)
    try:
        value = int(client.decr(key))
        if value < 0:
            client.set(key, "0", ex=ttl)
        else:
            client.expire(key, ttl)
    except Exception:
        log_sampling(logging.DEBUG, "采样 inflight 释放失败", phase=phase, job_id=job_id)


def reset_inflight_slot(job_id: UUID, phase: str, *, lane: str = "") -> None:
    phase = normalize_sampling_phase(phase)
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    redis_delete(_inflight_key(job_id, phase, lane=lane))


def reset_all_inflight_slots(job_id: UUID) -> None:
    for phase in SAMPLING_PHASES:
        reset_inflight_slot(job_id, phase)
        if phase == "llm":
            reset_inflight_slot(job_id, phase, lane="api")
            reset_inflight_slot(job_id, phase, lane="crawl")


def _soft_fail_orphaned_pending_llm(response_id: UUID) -> None:
    """Release reserved sampling quota when an LLM worker died holding the claim."""
    from aperix_geo.services.sampling.workflow.execute import (
        SOFT_SKIP_ORPHAN_CLAIM,
        mark_response_failed,
    )

    db = SessionLocal()
    try:
        row = db.execute(
            select(LLMResponse).where(LLMResponse.id == response_id).with_for_update()
        ).scalar_one_or_none()
        if row is None or row.status != LLMResponseStatus.pending:
            db.commit()
            return
        mark_response_failed(db, row=row, error_text=SOFT_SKIP_ORPHAN_CLAIM)
        db.commit()
    except Exception:
        db.rollback()
        log_sampling(
            logging.WARNING,
            "采样 orphan claim 释放预留失败",
            phase="llm",
            response_id=response_id,
        )
    finally:
        db.close()


def reclaim_stale_response_dispatch(
    job_id: UUID,
    phase: str,
    response_id: UUID,
    *,
    lane: str = "",
) -> None:
    """Drop orphaned dispatch/claim locks (worker died without on_task_finished)."""
    phase = normalize_sampling_phase(phase)
    client = shared_redis_client()
    if client is None:
        return
    key = _dispatch_key(phase, response_id)
    try:
        if not client.exists(key):
            return
    except Exception:
        return

    inflight_raw = client.get(_inflight_key(job_id, phase, lane=lane))
    inflight = int(inflight_raw or 0)
    # Also check unlane'd key for transition.
    if inflight <= 0 and lane:
        inflight = int(client.get(_inflight_key(job_id, phase)) or 0)
    claim_active = response_claim_active(response_id)

    # Active worker: claim held and inflight slot still reserved for this job/phase.
    if claim_active and inflight > 0:
        return
    # Orphaned: dispatch marker without inflight (or claim with no slot) — safe to reclaim.
    if claim_active:
        from aperix_geo.services.sampling.workflow.claim import release_response_claim

        release_response_claim(response_id)
        # LLM phase holds reserved quota; dead worker will never confirm — release now.
        if phase == "llm":
            _soft_fail_orphaned_pending_llm(response_id)
    release_response_dispatched(phase, response_id)


def try_mark_response_dispatched(
    job_id: UUID,
    phase: str,
    response_id: UUID,
    *,
    lane: str = "",
) -> bool:
    """Reserve a response so fill does not enqueue duplicate phase tasks."""
    phase = normalize_sampling_phase(phase)
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return True
    key = _dispatch_key(phase, response_id)
    ttl = _inflight_ttl_s(phase=phase, lane=lane)
    index_key = _dispatch_index_key(job_id, phase)
    marker = f"{job_id}|{lane}" if lane else str(job_id)
    try:
        if not client.set(key, marker, nx=True, ex=max(1, ttl)):
            return False
        client.sadd(index_key, str(response_id))
        client.expire(index_key, max(1, ttl))
        return True
    except Exception:
        log_sampling(
            logging.WARNING,
            "采样 dispatch 标记失败",
            phase=phase,
            job_id=job_id,
            response_id=response_id,
        )
        return False


def release_response_dispatched(phase: str, response_id: UUID) -> tuple[UUID | None, str]:
    """Clear dispatch marker; return (job_id, lane)."""
    phase = normalize_sampling_phase(phase)
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return None, ""
    key = _dispatch_key(phase, response_id)
    try:
        raw = client.get(key)
        client.delete(key)
        if not raw:
            return None, ""
        text = str(raw)
        lane = ""
        job_part = text
        if "|" in text:
            job_part, lane = text.split("|", 1)
        job_id = UUID(job_part)
        client.srem(_dispatch_index_key(job_id, phase), str(response_id))
        return job_id, lane
    except Exception:
        redis_delete(key)
        return None, ""


def reset_all_dispatch_markers(job_id: UUID) -> None:
    """Drop per-response dispatch locks after stale recovery."""
    client = shared_redis_client()
    if client is None:
        return
    for phase in SAMPLING_PHASES:
        index_key = _dispatch_index_key(job_id, phase)
        try:
            members = client.smembers(index_key) or []
            for raw_id in members:
                redis_delete(_dispatch_key(phase, UUID(str(raw_id))))
            redis_delete(index_key)
        except Exception:
            log_sampling(logging.DEBUG, "采样 dispatch 索引清理失败", phase=phase, job_id=job_id)


def _pending_responses_for_phase(
    db,
    job_id: UUID,
    phase: str,
    *,
    limit: int,
) -> list[LLMResponse]:
    phase = normalize_sampling_phase(phase)
    expected = phase_expected_status(phase)
    return list(
        db.execute(
            select(LLMResponse)
            .where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == expected,
            )
            .limit(limit)
        )
        .scalars()
        .all()
    )


def _llm_lane_and_task(platform: str) -> tuple[str, str]:
    from aperix_geo.services.sampling.backends import resolve_sampling_backend

    backend = resolve_sampling_backend(platform)
    if backend == "crawl":
        return "crawl", SAMPLING_LLM_CRAWL_TASK
    return "api", SAMPLING_LLM_API_TASK


def _crawl_lane_max_slots(db, platform: str) -> int:
    from aperix_geo.services.sampling.crawl_capacity import platform_crawl_pool_total

    settings = get_settings()
    total = platform_crawl_pool_total(db, platform, settings=settings)
    ceiling = max(1, int(settings.celery_crawl_worker_concurrency))
    return max(1, min(total if total > 0 else ceiling, ceiling))


def _send_phase_task(phase: str, response_id: str, *, task_name: str | None = None) -> None:
    from aperix_geo.celery_app import celery_app

    from aperix_geo.services.sampling.workflow.phases import phase_celery_task

    celery_app.send_task(task_name or phase_celery_task(phase), args=[response_id])


def fill_phase(job_id: str, phase: str) -> int:
    """Dispatch tasks until inflight cap or queue is empty."""
    phase = normalize_sampling_phase(phase)
    jid = UUID(job_id)
    settings = get_settings()
    max_slots = settings.sampling_max_inflight
    candidate_limit = max(max_slots * 4, 32)
    dispatched = 0
    while True:
        db = SessionLocal()
        try:
            rows = _pending_responses_for_phase(
                db,
                jid,
                phase,
                limit=candidate_limit,
            )
        finally:
            db.close()

        picked: LLMResponse | None = None
        lane = ""
        task_name: str | None = None
        lane_max = max_slots
        for row in rows:
            lane = ""
            task_name = None
            lane_max = max_slots
            if phase == "llm":
                lane, task_name = _llm_lane_and_task(str(row.platform or ""))
                if lane == "crawl":
                    db2 = SessionLocal()
                    try:
                        lane_max = _crawl_lane_max_slots(db2, str(row.platform or ""))
                    finally:
                        db2.close()
            reclaim_stale_response_dispatch(jid, phase, row.id, lane=lane)
            if try_mark_response_dispatched(jid, phase, row.id, lane=lane):
                picked = row
                break

        if picked is None:
            break

        if not try_reserve_inflight_slot(jid, phase, lane_max, lane=lane):
            release_response_dispatched(phase, picked.id)
            break

        _send_phase_task(phase, str(picked.id), task_name=task_name)
        dispatched += 1
    if dispatched > 0:
        _touch_sampling_job_activity(jid)
    return dispatched


def _touch_sampling_job_activity(job_id: UUID) -> None:
    """Keep stale recovery from treating a healthy backlog as abandoned."""
    from aperix_geo.db.base import utc_now
    from aperix_geo.db.models import SamplingJob

    db = SessionLocal()
    try:
        job = db.get(SamplingJob, job_id)
        if job is None:
            return
        job.updated_at = utc_now()
        db.commit()
    except Exception:
        db.rollback()
        log_sampling(logging.DEBUG, "采样 job activity touch 失败", job_id=job_id)
    finally:
        db.close()


def try_schedule_phase_fill(job_id: UUID, phase: str) -> bool:
    settings = get_settings()
    phase = normalize_sampling_phase(phase)
    return redis_set_nx_strict(
        f"aperix:sampling:fill:{job_id}:{phase}",
        ttl_s=settings.sampling_fill_debounce_seconds,
    )


def schedule_phase_fill(job_id: str, phase: str, *, force: bool = False) -> None:
    jid = UUID(job_id)
    phase = normalize_sampling_phase(phase)
    if not force and not try_schedule_phase_fill(jid, phase):
        return
    from aperix_geo.celery_app import celery_app

    celery_app.send_task(SAMPLING_FILL, args=[job_id, phase])


def dispatch_phases(job_id: str) -> bool:
    """Fill LLM / page / parse queues up to the in-flight cap for each phase."""
    dispatched_any = False
    for phase in SAMPLING_PHASES:
        count = fill_phase(job_id, phase)
        if count > 0:
            dispatched_any = True
            log_sampling(
                logging.INFO,
                "采样 fill 派发",
                phase=phase,
                job_id=job_id,
                batch_size=count,
            )
    if not dispatched_any:
        schedule_job_finalize(UUID(job_id))
    return dispatched_any


def _lookup_job_id(response_id: UUID, *, job_id: UUID | None) -> UUID | None:
    if job_id is not None:
        return job_id
    db = SessionLocal()
    try:
        row = db.get(LLMResponse, response_id)
        if row is None:
            return None
        return row.sampling_job_id
    finally:
        db.close()


def on_task_claim_lost(response_id: UUID, phase: str, *, job_id: UUID | None) -> None:
    """Duplicate worker for the same response: drop inflight only, keep dispatch marker."""
    phase = normalize_sampling_phase(phase)
    resolved = _lookup_job_id(response_id, job_id=job_id)
    if resolved is None:
        return
    # Best-effort release both lanes for llm.
    if phase == "llm":
        release_inflight_slot(resolved, phase, lane="api")
        release_inflight_slot(resolved, phase, lane="crawl")
    release_inflight_slot(resolved, phase)


def on_task_finished(response_id: UUID, phase: str, *, job_id: UUID | None = None) -> None:
    """Release dispatch + inflight, refill queue, and debounce job finalize."""
    phase = normalize_sampling_phase(phase)
    resolved, lane = release_response_dispatched(phase, response_id)
    if resolved is None:
        resolved = job_id
    if resolved is None:
        resolved = _lookup_job_id(response_id, job_id=None)
    if resolved is None:
        return

    release_inflight_slot(resolved, phase, lane=lane)
    schedule_phase_fill(str(resolved), phase)
    next_phase = NEXT_FILL_PHASE.get(phase)
    if next_phase is not None:
        # page → parse must not lose to fill debounce (llm may have scheduled parse too early).
        schedule_phase_fill(str(resolved), next_phase, force=(next_phase == "parse"))
    # No citation URLs → persist_llm_result jumps pending → crawl_ready (skips page).
    if phase == "llm":
        db = SessionLocal()
        try:
            row = db.get(LLMResponse, response_id)
            if row is not None and row.status == LLMResponseStatus.crawl_ready:
                schedule_phase_fill(str(resolved), "parse")
        finally:
            db.close()
    schedule_job_finalize(resolved)
