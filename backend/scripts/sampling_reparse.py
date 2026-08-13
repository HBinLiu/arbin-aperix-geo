#!/usr/bin/env python3
"""Re-run parse_llm_output on existing success responses and update parsed JSONB.

Env: loads backend/.env.{mode}; mode from ENV/APP_ENV or backend/.env.mode.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.execute import reparse_response_row
from aperix_geo.services.subject.loader import load_subject_with_competitors


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill parsed fields on LLM responses")
    parser.add_argument("--subject-id", help="Limit to a subject UUID")
    parser.add_argument("--dry-run", action="store_true", help="Count only, do not write")
    args = parser.parse_args()

    db = SessionLocal()
    updated = 0
    skipped = 0
    try:
        q = (
            select(LLMResponse)
            .join(SamplingJob, LLMResponse.sampling_job_id == SamplingJob.id)
            .where(
                LLMResponse.status == LLMResponseStatus.success,
                LLMResponse.raw_text.isnot(None),
            )
        )
        if args.subject_id:
            q = q.where(SamplingJob.subject_id == args.subject_id)
        rows = list(db.execute(q).scalars().all())
        for row in rows:
            job = db.get(SamplingJob, row.sampling_job_id)
            if not job:
                skipped += 1
                continue
            subject = load_subject_with_competitors(db, job.subject_id)
            if not subject:
                skipped += 1
                continue
            if args.dry_run:
                updated += 1
                continue
            try:
                reparse_response_row(db, row=row, subject=subject)
                db.commit()
                updated += 1
            except ValueError:
                db.rollback()
                skipped += 1
    finally:
        db.close()

    print(f"updated={updated} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
