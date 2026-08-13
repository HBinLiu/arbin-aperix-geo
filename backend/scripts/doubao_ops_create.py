#!/usr/bin/env python3
"""豆包运维：创建登录/验证码人工工单。

用途
----
主动开一张 pending 工单。若已配置 GEO_CRAWL_OPS_* 且本机 Docker 可用，
会顺带拉起 geo-crawl-ops 远程桌面，并返回 login_url 供浏览器登录/过验证码。

与采样的关系
------------
爬虫遇到登录失效/行为验证码时也会自动开工单；本脚本用于运维手动开单、
单独验收 noVNC，不必等采样报错。

账号池
------
生产 Cookie 存在 tb_doubao_accounts，本脚本不需要本地 storage_state 文件。
可选传入 --account-id，会把该账号已有 Cookie 注入远程桌面，便于重登/过码。

用法
----
  export PYTHONPATH=src
  # 环境：backend/.env.{mode}；mode = ENV/APP_ENV 或 backend/.env.mode（默认 development）
  # 生产：echo production > .env.mode
  # 建议用项目 .venv（Python ≥ 3.12）

  # 经 HTTP 调本机/生产 API（token 默认读配置里的 DOUBAO_OPS_API_TOKEN）
  ./.venv/bin/python scripts/doubao_ops_create.py \\
      --label prod-1 --operator alice --api-base http://127.0.0.1:8000

  # 直写数据库并 spawn（同一套 .env.mode → DATABASE_URL）
  ./.venv/bin/python scripts/doubao_ops_create.py \\
      --label prod-1 --operator alice --local

关单
----
  - 远程桌面登录成功且配置了 GEO_CRAWL_OPS_CALLBACK_BASE_URL → 一般会自动回传 Cookie
  - 否则用本机导出的 storage_state 跑：scripts/doubao_ops_complete.py
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


def _via_http(label: str, account_id: str | None, operator: str, base: str, token: str) -> int:
    """调用 POST /api/v1/ops/doubao/tickets 创建工单。"""
    import urllib.error
    import urllib.request

    body: dict = {"label": label, "operator": operator}
    if account_id:
        body["account_id"] = account_id
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/ops/doubao/tickets",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Doubao-Ops-Token": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.read().decode("utf-8"))
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        return 2


def _via_local(label: str, account_id: str | None, operator: str) -> int:
    """不经 HTTP，直接写库（并在配置齐全时 spawn 容器）。"""
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.doubao_accounts import tickets as ticket_svc

    db = SessionLocal()
    try:
        ticket = ticket_svc.create_login_ticket(
            db,
            label=label,
            account_id=UUID(account_id) if account_id else None,
            operator=operator,
        )
        db.commit()
        print(json.dumps(ticket_svc.ticket_to_dict(ticket), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="创建豆包登录/验证码人工工单（可选拉起 noVNC 远程桌面）"
    )
    parser.add_argument("--label", default="", help="账号 label；无 account-id 时用于新建池内标签")
    parser.add_argument("--account-id", default="", help="可选：已有账号 UUID，注入其 Cookie")
    parser.add_argument("--operator", default=os.environ.get("USER", "ops"), help="操作人备注")
    parser.add_argument(
        "--local",
        action="store_true",
        help="直写数据库（不调 HTTP）；需本进程能连目标库",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("APERIX_API_BASE", "http://127.0.0.1:8000"),
        help="Ops API 根地址（默认本机 8000）",
    )
    args = parser.parse_args()

    if args.local:
        return _via_local(args.label, args.account_id or None, args.operator)

    from aperix_geo.config import get_settings

    token = (os.environ.get("DOUBAO_OPS_API_TOKEN") or get_settings().doubao_ops_api_token or "").strip()
    if not token:
        print("请在 .env 中配置 DOUBAO_OPS_API_TOKEN，或 export 后重试，或改用 --local", file=sys.stderr)
        return 1
    return _via_http(args.label, args.account_id or None, args.operator, args.api_base, token)


if __name__ == "__main__":
    raise SystemExit(main())
