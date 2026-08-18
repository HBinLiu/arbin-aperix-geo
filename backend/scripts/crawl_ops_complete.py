#!/usr/bin/env python3
"""Crawl ops：用 storage_state 完成（关闭）登录工单。

用途
----
把「人工登录后」的 Playwright Cookie（storage_state JSON）提交给工单，
使对应账号回池为 active，工单变为 succeeded。headed Chrome 由 crawl 登录 watcher 自行关闭。

何时需要本脚本
--------------
- 未配 GEO_CRAWL_OPS_CALLBACK_BASE_URL，或容器自动回传失败 → 手动 upload 关单
- 本机登录脚本导出 Cookie 后，对着已开的工单关单（豆包：doubao_web_login.py）

何时不需要
----------
- 生产账号池日常采样：不读本地文件，只读库里的 tb_crawl_accounts
- noVNC 内登录成功且自动 complete-by-token 已成功 → 不必再跑本脚本

用法
----
  export PYTHONPATH=src

  ./.venv/bin/python scripts/crawl_ops_complete.py \\
      --ticket-id <创建工单返回的 uuid> \\
      --state data/doubao_storage_state.json \\
      --api-base http://127.0.0.1:8000

  # 或直写库
  ./.venv/bin/python scripts/crawl_ops_complete.py \\
      --ticket-id <uuid> --state data/doubao_storage_state.json --local
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="上传 storage_state 完成登录工单（写入账号池并关单）"
    )
    parser.add_argument("--ticket-id", required=True, help="工单 UUID（create 脚本输出的 id）")
    parser.add_argument(
        "--state",
        type=Path,
        required=True,
        help="Playwright storage_state.json（登录后导出的 Cookie，用于更新账号池）",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="直写数据库（不调 HTTP）",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("APERIX_API_BASE", "http://127.0.0.1:8000"),
        help="Ops API 根地址",
    )
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"找不到 state 文件: {args.state}", file=sys.stderr)
        return 1
    storage_state = json.loads(args.state.read_text(encoding="utf-8"))

    if args.local:
        from aperix_geo.db.session import SessionLocal
        from aperix_geo.services.crawl_accounts import tickets as ticket_svc
        from aperix_geo.services.crawl_accounts.pool import account_to_dict

        db = SessionLocal()
        try:
            ticket, account = ticket_svc.complete_ticket_with_storage_state(
                db,
                UUID(args.ticket_id),
                storage_state=storage_state,
            )
            db.commit()
            print(
                json.dumps(
                    {
                        "ticket": ticket_svc.ticket_to_dict(ticket),
                        "account": account_to_dict(account),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        except Exception as exc:
            db.rollback()
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        finally:
            db.close()

    import urllib.error
    import urllib.request

    from aperix_geo.config import get_settings

    token = (
        os.environ.get("GEO_CRAWL_OPS_API_TOKEN") or get_settings().geo_crawl_ops_api_token or ""
    ).strip()
    if not token:
        print(
            "请在 .env 中配置 GEO_CRAWL_OPS_API_TOKEN，或 export 后重试，或改用 --local",
            file=sys.stderr,
        )
        return 1
    req = urllib.request.Request(
        f"{args.api_base.rstrip('/')}/api/v1/ops/geo-crawl/tickets/{args.ticket_id}/complete",
        data=json.dumps({"storage_state": storage_state}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Geo-Crawl-Ops-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.read().decode("utf-8"))
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
