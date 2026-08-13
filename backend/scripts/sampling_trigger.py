#!/usr/bin/env python3
"""Trigger one sampling job for a subject (direct DB + Celery enqueue).

Env: loads backend/.env.{mode}; mode from ENV/APP_ENV or backend/.env.mode
(default development). Production: ``echo production > .env.mode``.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from sqlalchemy import select

from aperix_geo.db.models import Subject
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, enqueue_subject_sampling
from aperix_geo.services.subject.loader import load_subject_with_competitors


def list_subjects(db) -> list[Subject]:
    return list(db.execute(select(Subject).order_by(Subject.created_at.desc())).scalars().all())


def trigger_direct(db, subject_id: UUID) -> dict:
    subject = load_subject_with_competitors(db, subject_id)
    if not subject:
        raise SystemExit(f"Subject not found: {subject_id}")
    try:
        job = enqueue_subject_sampling(db, subject=subject)
    except SamplingJobError as e:
        raise SystemExit(str(e)) from e
    return {
        "job_id": str(job.id),
        "subject_id": str(subject.id),
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "total_items": job.total_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger one sampling job for a subject")
    parser.add_argument("--subject-id", help="Subject UUID (default: most recent subject)")
    parser.add_argument("--list", action="store_true", help="List subjects and exit")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            rows = list_subjects(db)
            if not rows:
                print("No subjects found.")
                return 0
            for s in rows:
                label = s.domain or s.brand or str(s.id)
                print(f"{s.id}\t{label}")
            return 0

        subject_id: UUID
        if args.subject_id:
            subject_id = UUID(args.subject_id)
        else:
            rows = list_subjects(db)
            if not rows:
                raise SystemExit("No subjects in database; pass --subject-id")
            subject_id = rows[0].id
            label = rows[0].domain or rows[0].brand or str(rows[0].id)
            print(f"Using latest subject: {subject_id} ({label})")

        result = trigger_direct(db, subject_id)
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
