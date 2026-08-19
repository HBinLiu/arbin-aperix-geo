#!/usr/bin/env python3
"""Resume sampling fill (llm / page / parse) for a stuck job.

Use when Overview stays on「语义清洗降噪」but browser crawl already finished.
Requires backend venv Python >= 3.12 (not host ``python3`` on CentOS 7).

Usage (from backend/):

  .venv/bin/python scripts/sampling_continue.py <job_id> --status-only
  .venv/bin/python scripts/sampling_continue.py <job_id> --reset-locks
  .venv/bin/python scripts/sampling_continue.py <job_id> --reset-locks --inline
  .venv/bin/python scripts/sampling_continue.py <job_id> --celery
  .venv/bin/python scripts/sampling_continue.py --recover --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class _InlineTask:
    """Minimal Celery task stand-in for run_sampling_phase in ops scripts."""

    class _Request:
        retries = 0

    request = _Request()

    def retry(self, **_kwargs: object) -> None:
        raise RuntimeError("inline sampling phase retry not supported")


def _job_status(job_id: UUID) -> dict[str, Any]:
    from sqlalchemy import func, select

    from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.sampling.workflow.status import build_pipeline_status

    db = SessionLocal()
    try:
        job = db.get(SamplingJob, job_id)
        if job is None:
            raise SystemExit(f"sampling job not found: {job_id}")
        counts = dict(
            db.execute(
                select(LLMResponse.status, func.count(LLMResponse.id))
                .where(LLMResponse.sampling_job_id == job_id)
                .group_by(LLMResponse.status)
            ).all()
        )
        pending_rows = list(
            db.execute(
                select(LLMResponse)
                .where(
                    LLMResponse.sampling_job_id == job_id,
                    LLMResponse.status.in_(
                        (
                            LLMResponseStatus.llm_ready,
                            LLMResponseStatus.crawl_ready,
                            LLMResponseStatus.pending,
                        )
                    ),
                )
                .order_by(LLMResponse.created_at)
            )
            .scalars()
            .all()
        )
        pipeline = build_pipeline_status(db, subject_id=job.subject_id)
        return {
            "job_id": str(job_id),
            "subject_id": str(job.subject_id),
            "job_status": job.status.value,
            "response_status_counts": {
                (status.value if hasattr(status, "value") else str(status)): int(count)
                for status, count in counts.items()
            },
            "pipeline_stage": pipeline.get("stage"),
            "worker_phase": pipeline.get("worker_phase"),
            "parsed_count": pipeline.get("parsed_count"),
            "response_count": pipeline.get("response_count"),
            "crawl_ready_count": pipeline.get("crawl_ready_count"),
            "llm_ready_count": pipeline.get("llm_ready_count"),
            "llm_pending_count": pipeline.get("llm_pending_count"),
            "pending_responses": [
                {
                    "id": str(row.id),
                    "platform": row.platform,
                    "status": row.status.value,
                    "raw_text_len": len(row.raw_text or ""),
                    "share_url_set": bool((row.share_url or "").strip()),
                    "error_text": (row.error_text or "")[:200],
                }
                for row in pending_rows
            ],
        }
    finally:
        db.close()


def _reset_job_locks(job_id: UUID) -> None:
    from aperix_geo.services.sampling.workflow.fill import (
        reset_all_dispatch_markers,
        reset_all_inflight_slots,
    )

    reset_all_inflight_slots(job_id)
    reset_all_dispatch_markers(job_id)


def _run_inline_phases(job_id: UUID) -> list[dict[str, Any]]:
    """Run page/parse synchronously for rows still on llm_ready / crawl_ready."""
    from sqlalchemy import select

    from aperix_geo.db.models import LLMResponse, LLMResponseStatus
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db
    from aperix_geo.services.sampling.workflow.phase import run_sampling_phase
    from aperix_geo.services.sampling.workflow.phase_specs import (
        build_page_phase_spec,
        build_parse_phase_spec,
    )

    task = _InlineTask()
    results: list[dict[str, Any]] = []

    db = SessionLocal()
    try:
        rows = list(
            db.execute(
                select(LLMResponse)
                .where(
                    LLMResponse.sampling_job_id == job_id,
                    LLMResponse.status.in_(
                        (LLMResponseStatus.llm_ready, LLMResponseStatus.crawl_ready)
                    ),
                )
                .order_by(LLMResponse.created_at)
            )
            .scalars()
            .all()
        )
    finally:
        db.close()

    for row in rows:
        rid = str(row.id)
        if row.status == LLMResponseStatus.llm_ready:
            out = run_sampling_phase(task, rid, build_page_phase_spec(task, rid))
            results.append({"response_id": rid, "phase": "page", **out})
            if not out.get("ok"):
                continue
        out = run_sampling_phase(task, rid, build_parse_phase_spec(task, rid))
        results.append({"response_id": rid, "phase": "parse", **out})

    db = SessionLocal()
    try:
        finalize_sampling_job_db(db, job_id)
    finally:
        db.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="续跑采样 job 的 llm/page/parse fill")
    parser.add_argument("job_id", nargs="?", help="Sampling job UUID")
    parser.add_argument(
        "--celery",
        action="store_true",
        help="经 Celery 入队 sampling_dispatch(bootstrap=false)，而非本进程直接 fill",
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help="扫描并恢复所有卡住 job（等同 sampling_recover task）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="与 --recover 合用：不等待 stale 窗口",
    )
    parser.add_argument(
        "--reset-locks",
        action="store_true",
        help="清除该 job 的 Redis dispatch / inflight 锁后再派发",
    )
    parser.add_argument(
        "--inline",
        action="store_true",
        help="本进程同步跑 page+parse（绕过 Celery，适合 parse worker 未消费队列时）",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="只打印 job / pipeline 状态，不派发",
    )
    args = parser.parse_args()

    if args.recover:
        from aperix_geo.db.session import SessionLocal
        from aperix_geo.services.sampling.workflow.recovery import recover_stale_sampling_jobs

        db = SessionLocal()
        try:
            recovered = recover_stale_sampling_jobs(db, force=args.force)
        finally:
            db.close()
        print(json.dumps({"recovered": recovered, "force": args.force}, ensure_ascii=False, indent=2))
        return 0

    if not args.job_id:
        parser.error("job_id required unless --recover")

    job_id = UUID(args.job_id.strip())
    before = _job_status(job_id)
    print(json.dumps({"before": before}, ensure_ascii=False, indent=2))

    if args.status_only:
        return 0

    if args.reset_locks:
        _reset_job_locks(job_id)
        print(json.dumps({"reset_locks": True}, ensure_ascii=False, indent=2))

    if args.inline:
        inline_results = _run_inline_phases(job_id)
        after = _job_status(job_id)
        print(
            json.dumps(
                {"inline_results": inline_results, "after": after},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.celery:
        from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_continue

        enqueue_sampling_continue(job_id)
        print(json.dumps({"queued": True, "via": "celery_dispatch"}, ensure_ascii=False, indent=2))
    else:
        from aperix_geo.services.sampling.workflow.fill import dispatch_phases

        dispatched = dispatch_phases(str(job_id))
        after = _job_status(job_id)
        print(
            json.dumps(
                {"dispatched": dispatched, "via": "direct_fill", "after": after},
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
