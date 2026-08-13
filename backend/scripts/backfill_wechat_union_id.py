#!/usr/bin/env python3
"""Backfill tb_users.union_id from WeChat MP user/info.

Prerequisites:
  1. Service account (公众号) is linked under the same WeChat Open Platform account.
  2. WECHAT_APP_ID / WECHAT_APP_SECRET configured.
  3. Users already have open_id (from QR bind) and empty union_id.

Usage (from backend/):

  uv run python scripts/backfill_wechat_union_id.py --dry-run
  uv run python scripts/backfill_wechat_union_id.py

Env: backend/.env.{mode} via ENV/APP_ENV or backend/.env.mode (default development).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill WeChat union_id for bound users")
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to process (0=all)")
    args = parser.parse_args()

    from sqlalchemy import select

    from aperix_geo.config import get_settings
    from aperix_geo.db.models import User
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.wechat.config import wechat_configured
    from aperix_geo.services.wechat.token import WechatError
    from aperix_geo.services.wechat.user_info import fetch_user_info

    settings = get_settings()
    if not wechat_configured(settings):
        print("ERROR: WECHAT_* not configured", file=sys.stderr)
        return 1

    db = SessionLocal()
    updated = skipped = failed = 0
    try:
        q = select(User).where(User.open_id != "", User.union_id == "")
        if args.limit > 0:
            q = q.limit(args.limit)
        users = list(db.execute(q).scalars().all())
        print(f"candidates={len(users)} dry_run={args.dry_run}")

        for user in users:
            try:
                info = fetch_user_info(user.open_id, settings=settings)
            except WechatError as exc:
                print(f"FAIL user={user.id} openid={user.open_id[:8]}… err={exc}")
                failed += 1
                continue
            if info is None or not info.union_id:
                skipped += 1
                continue
            if args.dry_run:
                print(f"DRY user={user.id} would set union_id={info.union_id[:8]}…")
                updated += 1
                continue
            user.union_id = info.union_id
            if info.nick_name and not user.nick_name.strip():
                user.nick_name = info.nick_name
            db.commit()
            updated += 1
            print(f"OK user={user.id} union_id={info.union_id[:8]}…")

        print(f"done updated={updated} skipped={skipped} failed={failed}")
        return 0 if failed == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
