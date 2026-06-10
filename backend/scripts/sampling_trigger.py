#!/usr/bin/env python3
"""Trigger one sampling job for a subject (local dev).

Default: in-process via enqueue_subject_sampling.
Use --via-api to hit the HTTP debug route (requires SAMPLING_DEBUG_* and running API).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from uuid import UUID

from sqlalchemy import select

from aperix_geo.config import get_settings
from aperix_geo.db.models import Subject
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.sampling.workflow import SamplingJobError, enqueue_subject_sampling
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
        "mode": "direct",
        "job_id": str(job.id),
        "subject_id": str(subject.id),
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "total_items": job.total_items,
    }


def trigger_via_api(subject_id: UUID, base_url: str, secret: str) -> dict:
    url = f"{base_url.rstrip('/')}/api/v1/dev/subjects/{subject_id}/sampling-jobs"
    req = urllib.request.Request(
        url,
        method="POST",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Aperix-Sampling-Debug": secret,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Request failed: {e.reason}") from e
    return {"mode": "api", **body}


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger one sampling job for a subject")
    parser.add_argument("--subject-id", help="Subject UUID (default: most recent subject)")
    parser.add_argument("--list", action="store_true", help="List subjects and exit")
    parser.add_argument(
        "--via-api",
        action="store_true",
        help="Call HTTP debug route (needs SAMPLING_DEBUG_ENABLED + running API)",
    )
    parser.add_argument(
        "--api-base-url",
        help="API base URL for --via-api (default: http://127.0.0.1:{API_PORT})",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            rows = list_subjects(db)
            if not rows:
                print("No subjects found.")
                return 0
            for s in rows:
                label = s.domain or s.brand_name or str(s.id)
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
            label = rows[0].domain or rows[0].brand_name or str(rows[0].id)
            print(f"Using latest subject: {subject_id} ({label})")

        if args.via_api:
            settings = get_settings()
            if not settings.sampling_debug_enabled or not settings.sampling_debug_secret:
                raise SystemExit(
                    "Set SAMPLING_DEBUG_ENABLED=true and SAMPLING_DEBUG_SECRET in backend/.env"
                )
            base = args.api_base_url or f"http://127.0.0.1:{settings.api_port}"
            result = trigger_via_api(subject_id, base, settings.sampling_debug_secret)
        else:
            result = trigger_direct(db, subject_id)
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
