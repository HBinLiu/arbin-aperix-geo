#!/usr/bin/env python3
"""删除因订阅到期或 AI 额度用尽而失败的采样任务（默认 dry-run）。

匹配规则：
- job.created_at 在 --since-days 内（默认 3）
- 至少有一条 LLMResponse
- 全部 response 均为 failed，且 error_text 匹配到期/额度文案
  （无成功样本，可安全整单删除；级联删除 response / signals / citations）

用法：
  uv run python scripts/failed_sampling_cleanup.py
  uv run python scripts/failed_sampling_cleanup.py --apply
  uv run python scripts/failed_sampling_cleanup.py --since-days 2 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, Subject
from aperix_geo.db.session import SessionLocal

_ERROR_MARKERS = (
    "AI 调用额度已用尽",
    "订阅已过期",
)


def _matches_quota_or_expired(error_text: str) -> bool:
    text = (error_text or "").strip()
    return any(marker in text for marker in _ERROR_MARKERS)


def find_candidate_job_ids(db, *, since: datetime) -> list[UUID]:
    jobs = list(
        db.execute(
            select(SamplingJob)
            .where(SamplingJob.created_at >= since)
            .order_by(SamplingJob.created_at.desc())
        )
        .scalars()
        .all()
    )
    if not jobs:
        return []

    job_ids = [job.id for job in jobs]
    rows = list(
        db.execute(
            select(
                LLMResponse.sampling_job_id,
                LLMResponse.status,
                LLMResponse.error_text,
            ).where(LLMResponse.sampling_job_id.in_(job_ids))
        ).all()
    )

    by_job: dict[UUID, list[tuple[LLMResponseStatus, str]]] = {}
    for job_id, status, error_text in rows:
        by_job.setdefault(job_id, []).append((status, error_text or ""))

    candidates: list[UUID] = []
    for job in jobs:
        items = by_job.get(job.id) or []
        if not items:
            continue
        if any(status != LLMResponseStatus.failed for status, _ in items):
            continue
        if not all(_matches_quota_or_expired(error_text) for _, error_text in items):
            continue
        candidates.append(job.id)
    return candidates


def summarize_jobs(db, job_ids: list[UUID]) -> list[dict]:
    if not job_ids:
        return []
    jobs = list(
        db.execute(select(SamplingJob).where(SamplingJob.id.in_(job_ids))).scalars().all()
    )
    subjects = {
        row.id: row
        for row in db.execute(
            select(Subject).where(Subject.id.in_({job.subject_id for job in jobs}))
        )
        .scalars()
        .all()
    }
    counts = dict(
        db.execute(
            select(LLMResponse.sampling_job_id, func.count())
            .where(LLMResponse.sampling_job_id.in_(job_ids))
            .group_by(LLMResponse.sampling_job_id)
        ).all()
    )
    out: list[dict] = []
    for job in sorted(jobs, key=lambda j: j.created_at, reverse=True):
        subject = subjects.get(job.subject_id)
        label = (subject.brand if subject else "") or (subject.domain if subject else "") or ""
        out.append(
            {
                "job_id": str(job.id),
                "tenant_id": str(job.tenant_id),
                "subject_id": str(job.subject_id),
                "subject": label,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "created_at": job.created_at.isoformat(),
                "total_items": job.total_items,
                "failed_items": job.failed_items,
                "response_count": int(counts.get(job.id, 0)),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup sampling jobs failed by quota/expiry")
    parser.add_argument("--since-days", type=float, default=3.0, help="Look back window in days (default 3)")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default is dry-run)")
    args = parser.parse_args()

    since = datetime.now(UTC) - timedelta(days=args.since_days)
    db = SessionLocal()
    try:
        job_ids = find_candidate_job_ids(db, since=since)
        summary = summarize_jobs(db, job_ids)
        payload = {
            "since": since.isoformat(),
            "candidate_jobs": len(summary),
            "apply": bool(args.apply),
            "jobs": summary,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        if not job_ids:
            print("No matching jobs.", file=sys.stderr)
            return 0
        if not args.apply:
            print("Dry-run only. Re-run with --apply to delete.", file=sys.stderr)
            return 0

        result = db.execute(delete(SamplingJob).where(SamplingJob.id.in_(job_ids)))
        db.commit()
        print(f"Deleted {result.rowcount} sampling job(s).", file=sys.stderr)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
