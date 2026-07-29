#!/usr/bin/env python3
"""Create a Doubao login ticket via ops API (or local DB when --local).

Usage:

  export DOUBAO_OPS_API_TOKEN=...
  export DOUBAO_LOGIN_TICKET_ENABLED=true
  python3 scripts/doubao_ticket_create.py --label staging-1 --operator alice

  # Complete after headed login:
  python3 scripts/doubao_ticket_complete.py --ticket-id <uuid> --state data/doubao_storage_state.json
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
    parser = argparse.ArgumentParser(description="Create Doubao login ticket")
    parser.add_argument("--label", default="")
    parser.add_argument("--account-id", default="")
    parser.add_argument("--operator", default=os.environ.get("USER", "ops"))
    parser.add_argument("--local", action="store_true", help="Write DB directly (no HTTP)")
    parser.add_argument("--api-base", default=os.environ.get("APERIX_API_BASE", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    if args.local:
        return _via_local(args.label, args.account_id or None, args.operator)

    token = (os.environ.get("DOUBAO_OPS_API_TOKEN") or "").strip()
    if not token:
        print("Set DOUBAO_OPS_API_TOKEN or pass --local", file=sys.stderr)
        return 1
    return _via_http(args.label, args.account_id or None, args.operator, args.api_base, token)


if __name__ == "__main__":
    raise SystemExit(main())
