#!/usr/bin/env python3
"""Upsert a crawl pool account from storage_state.json into tb_crawl_accounts.

Usage (from backend/):

  export PYTHONPATH=src
  python3 scripts/crawl_account_upsert.py \\
    --platform doubao \\
    --label staging-1 \\
    --state data/doubao_storage_state.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.db.session import SessionLocal  # noqa: E402
from aperix_geo.services.crawl_accounts.pool import upsert_account_from_state  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert crawl account into DB pool")
    parser.add_argument(
        "--platform",
        default="doubao",
        help="平台 id（doubao / deepseek / qianwen；默认 doubao）",
    )
    parser.add_argument("--label", required=True, help="Unique account label")
    parser.add_argument("--state", type=Path, required=True, help="Playwright storage_state JSON")
    args = parser.parse_args()
    platform = (args.platform or "doubao").strip().lower() or "doubao"

    if not args.state.is_file():
        print(f"state file not found: {args.state}", file=sys.stderr)
        return 1
    try:
        data = json.loads(args.state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        row = upsert_account_from_state(
            db,
            label=args.label,
            storage_state=data,
            platform=platform,
        )
        db.commit()
        print(
            f"upserted id={row.id} platform={row.platform} label={row.label!r} "
            f"status={row.status} last_ok_at={row.last_ok_at.isoformat()}"
        )
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
