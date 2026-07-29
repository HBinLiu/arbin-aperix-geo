#!/usr/bin/env python3
"""Complete a Doubao login ticket by uploading storage_state (noVNC fallback)."""

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
    parser = argparse.ArgumentParser(description="Complete Doubao login ticket with storage_state")
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--api-base", default=os.environ.get("APERIX_API_BASE", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state file not found: {args.state}", file=sys.stderr)
        return 1
    storage_state = json.loads(args.state.read_text(encoding="utf-8"))

    if args.local:
        from aperix_geo.db.session import SessionLocal
        from aperix_geo.services.doubao_accounts import tickets as ticket_svc

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
                        "account": ticket_svc.account_to_dict(account),
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

    token = (os.environ.get("DOUBAO_OPS_API_TOKEN") or "").strip()
    if not token:
        print("Set DOUBAO_OPS_API_TOKEN or pass --local", file=sys.stderr)
        return 1
    req = urllib.request.Request(
        f"{args.api_base.rstrip('/')}/api/v1/ops/doubao/tickets/{args.ticket_id}/complete",
        data=json.dumps({"storage_state": storage_state}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Doubao-Ops-Token": token},
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
