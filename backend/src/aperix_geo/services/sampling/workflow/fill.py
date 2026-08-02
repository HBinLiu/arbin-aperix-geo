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
    SAMPLING_PHASES,
    is_sampling_phase,
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


def _inflight_key(job_id: UUID, phase: str) -> str:
    return f"aperix:sampling:inflight:{job_id}:{phase}"


def _dispatch_key(phase: str, response_id: UUID) -> str:
    return f"aperix:sampling:dispatch:{phase}:{response_id}"


def _dispatch_index_key(job_id: UUID, phase: str) -> str:
    return f"aperix:sampling:dispatch_index:{job_id}:{phase}"


def _inflight_ttl_s() -> int:
    settings = get_settings()
    return min(3600, max(600, settings.sampling_stale_job_seconds * 20))


def try_reserve_inflight_slot(job_id: UUID, phase: str, max_slots: int) -> bool:
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return True
    key = _inflight_key(job_id, phase)
    ttl = _inflight_ttl_s()
    try:
        result = client.eval(_ACQUIRE_INFLIGHT_SCRIPT, 1, key, max_slots, ttl)
        return int(result) == 1
    except Exception:
        log_sampling(logging.WARNING, "采样 inflight 预留失败", phase=phase, job_id=job_id)
        return True


def release_inflight_slot(job_id: UUID, phase: str) -> None:
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return
    key = _inflight_key(job_id, phase)
    ttl = _inflight_ttl_s()
    try:
        value = int(client.decr(key))
        if value < 0:
            client.set(key, "0", ex=ttl)
        else:
            client.expire(key, ttl)
    except Exception:
        log_sampling(logging.DEBUG, "采样 inflight 释放失败", phase=phase, job_id=job_id)


def reset_inflight_slot(job_id: UUID, phase: str) -> None:
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    redis_delete(_inflight_key(job_id, phase))


def reset_all_inflight_slots(job_id: UUID) -> None:
    for phase in SAMPLING_PHASES:
        reset_inflight_slot(job_id, phase)


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


def reclaim_stale_response_dispatch(job_id: UUID, phase: str, response_id: UUID) -> None:
    """Drop orphaned dispatch/claim locks (worker died without on_task_finished)."""
    client = shared_redis_client()
    if client is None:
        return
    key = _dispatch_key(phase, response_id)
    try:
        if not client.exists(key):
            return
    except Exception:
        return

    inflight_raw = client.get(_inflight_key(job_id, phase))
    inflight = int(inflight_raw or 0)
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


def try_mark_response_dispatched(job_id: UUID, phase: str, response_id: UUID) -> bool:
    """Reserve a response so fill does not enqueue duplicate phase tasks."""
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return True
    key = _dispatch_key(phase, response_id)
    ttl = _inflight_ttl_s()
    index_key = _dispatch_index_key(job_id, phase)
    try:
        if not client.set(key, str(job_id), nx=True, ex=max(1, ttl)):
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


def release_response_dispatched(phase: str, response_id: UUID) -> UUID | None:
    """Clear dispatch marker; return job_id stored at mark time when available."""
    if not is_sampling_phase(phase):
        raise ValueError(f"invalid sampling fill phase: {phase}")
    client = shared_redis_client()
    if client is None:
        return None
    key = _dispatch_key(phase, response_id)
    try:
        job_id_str = client.get(key)
        client.delete(key)
        if not job_id_str:
            return None
        job_id = UUID(str(job_id_str))
        client.srem(_dispatch_index_key(job_id, phase), str(response_id))
        return job_id
    except Exception:
        redis_delete(key)
        return None


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


def _pending_response_ids_for_phase(
    db,
    job_id: UUID,
    phase: str,
    *,
    limit: int,
) -> list[UUID]:
    expected = phase_expected_status(phase)
    return list(
        db.execute(
            select(LLMResponse.id).where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == expected,
            ).limit(limit)
        ).scalars().all()
    )


def _send_phase_task(phase: str, response_id: str) -> None:
    from aperix_geo.celery_app import celery_app

    from aperix_geo.services.sampling.workflow.phases import phase_celery_task

    celery_app.send_task(phase_celery_task(phase), args=[response_id])


def fill_phase(job_id: str, phase: str) -> int:
    """Dispatch tasks until inflight cap or queue is empty."""
    jid = UUID(job_id)
    settings = get_settings()
    max_slots = settings.sampling_max_inflight
    candidate_limit = max(max_slots * 4, 32)
    dispatched = 0
    while True:
        db = SessionLocal()
        try:
            candidates = _pending_response_ids_for_phase(
                db,
                jid,
                phase,
                limit=candidate_limit,
            )
        finally:
            db.close()

        response_id: UUID | None = None
        for candidate in candidates:
            # Reclaim before inflight++ so job-level inflight=0 detects orphan locks.
            reclaim_stale_response_dispatch(jid, phase, candidate)
            if try_mark_response_dispatched(jid, phase, candidate):
                response_id = candidate
                break

        if response_id is None:
            break

        if not try_reserve_inflight_slot(jid, phase, max_slots):
            release_response_dispatched(phase, response_id)
            break

        _send_phase_task(phase, str(response_id))
        dispatched += 1
    return dispatched


def try_schedule_phase_fill(job_id: UUID, phase: str) -> bool:
    settings = get_settings()
    return redis_set_nx_strict(
        f"aperix:sampling:fill:{job_id}:{phase}",
        ttl_s=settings.sampling_fill_debounce_seconds,
    )


def schedule_phase_fill(job_id: str, phase: str) -> None:
    jid = UUID(job_id)
    if not try_schedule_phase_fill(jid, phase):
        return
    from aperix_geo.celery_app import celery_app

    celery_app.send_task(SAMPLING_FILL, args=[job_id, phase])


def dispatch_phases(job_id: str) -> bool:
    """Fill LLM / crawl / parse queues up to the in-flight cap for each phase."""
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
    resolved = _lookup_job_id(response_id, job_id=job_id)
    if resolved is not None:
        release_inflight_slot(resolved, phase)


def on_task_finished(response_id: UUID, phase: str, *, job_id: UUID | None = None) -> None:
    """Release dispatch + inflight, refill queue, and debounce job finalize."""
    resolved = release_response_dispatched(phase, response_id) or job_id
    if resolved is None:
        resolved = _lookup_job_id(response_id, job_id=None)
    if resolved is None:
        return

    release_inflight_slot(resolved, phase)
    schedule_phase_fill(str(resolved), phase)
    next_phase = NEXT_FILL_PHASE.get(phase)
    if next_phase is not None:
        schedule_phase_fill(str(resolved), next_phase)
    schedule_job_finalize(resolved)
