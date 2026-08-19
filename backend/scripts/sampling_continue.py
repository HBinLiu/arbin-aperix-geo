#!/usr/bin/env python3
"""Resume sampling fill (llm / page / parse) for a stuck job.

Use when Overview stays on「语义清洗降噪」but browser crawl already finished.
Requires backend venv Python >= 3.12 (not host ``python3`` on CentOS 7).

Usage (from backend/):

  .venv/bin/python scripts/sampling_continue.py <job_id>
  .venv/bin/python scripts/sampling_continue.py <job_id> --celery
  .venv/bin/python scripts/sampling_continue.py --recover --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _job_status(job_id: UUID) -> dict:
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
            "parsed_count": pipeline.get("parsed_count"),
            "response_count": pipeline.get("response_count"),
            "crawl_ready_count": pipeline.get("crawl_ready_count"),
            "llm_ready_count": pipeline.get("llm_ready_count"),
        }
    finally:
        db.close()


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
        "--status-only",
        action="store_true",
        help="只打印 job / pipeline 状态，不派发",
    )
    args = parser.parse_args()

    if args.recover:
        from aperix_geo.services.sampling.workflow.recovery import recover_stale_sampling_jobs
        from aperix_geo.db.session import SessionLocal

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
