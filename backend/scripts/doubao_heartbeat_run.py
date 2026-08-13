#!/usr/bin/env python3
"""豆包运维：手动触发一次账号池心跳（登录探活）。

用途
----
立刻跑一轮 ``run_doubao_account_heartbeat``：探活 active / need_relogin 等账号；
失败时按配置开登录工单（需 ``DOUBAO_OPS_TICKET_ENABLED``）。

用法
----
  cd backend
  export PYTHONPATH=src
  # 环境：backend/.env.{mode}；mode = ENV/APP_ENV 或 backend/.env.mode
  # 生产：echo production > .env.mode

  ./.venv/bin/python scripts/doubao_heartbeat_run.py
  ./.venv/bin/python scripts/doubao_heartbeat_run.py --force   # 即使 HEARTBEAT_ENABLED=false 也跑
  ./.venv/bin/python scripts/doubao_heartbeat_run.py --celery  # 丢给 worker 异步执行
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="手动触发一次豆包账号心跳探活")
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略 DOUBAO_HEARTBEAT_ENABLED=false，本轮强制探活",
    )
    parser.add_argument(
        "--celery",
        action="store_true",
        help="经 Celery 异步执行（受 HEARTBEAT_ENABLED 约束；--force 仅对直跑有效）",
    )
    args = parser.parse_args()

    if args.celery:
        from aperix_geo.tasks.doubao_accounts import doubao_account_heartbeat

        async_result = doubao_account_heartbeat.delay()
        print(json.dumps({"queued": True, "task_id": async_result.id}, ensure_ascii=False, indent=2))
        return 0

    from aperix_geo.config import get_settings
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.doubao_accounts.heartbeat import run_doubao_account_heartbeat

    settings = get_settings()
    if args.force and not settings.doubao_heartbeat_enabled:
        settings = settings.model_copy(update={"doubao_heartbeat_enabled": True})

    db = SessionLocal()
    try:
        result = run_doubao_account_heartbeat(db, settings=settings)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("skipped"):
            print(
                "心跳未执行：请设 DOUBAO_HEARTBEAT_ENABLED=true，或加 --force",
                file=sys.stderr,
            )
            return 2
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
