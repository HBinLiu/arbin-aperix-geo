#!/usr/bin/env python3
"""将某用户所在租户指派为指定订阅计划（等同完成订阅，无需支付）。

环境：加载 backend/.env.{mode}；mode = ENV/APP_ENV 或 backend/.env.mode（默认 development）。

Usage（在 backend/ 下）:

  uv run python scripts/assign_subscription.py --list-plans
  uv run python scripts/assign_subscription.py --list-users
  uv run python scripts/assign_subscription.py --phone 13800138000 --plan personal
  uv run python scripts/assign_subscription.py --email a@b.com --plan premium --cycle yearly
  uv run python scripts/assign_subscription.py --user-id <uuid> --plan ultimate --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign a subscription plan to a user's tenant")
    parser.add_argument("--list-plans", action="store_true", help="List active plans and exit")
    parser.add_argument("--list-users", action="store_true", help="List recent users and exit")
    parser.add_argument("--user-id", help="User UUID")
    parser.add_argument("--phone", help="User phone")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--plan", help="Plan code: personal / premium / ultimate / enterprise")
    parser.add_argument(
        "--cycle",
        default="monthly",
        choices=("monthly", "quarterly", "yearly"),
        help="Billing cycle (default: monthly)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show target without writing")
    args = parser.parse_args()

    from sqlalchemy import select

    from aperix_geo.db.models import Plan, TenantSubscription, User
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.billing.payments import assign_subscription_plan

    db = SessionLocal()
    try:
        if args.list_plans:
            plans = list(
                db.execute(
                    select(Plan)
                    .where(Plan.is_active.is_(True), Plan.deleted.is_(False))
                    .order_by(Plan.sort_order.asc())
                )
                .scalars()
                .all()
            )
            for plan in plans:
                print(
                    f"{plan.code}\t{plan.name}\t"
                    f"subjects={plan.max_subjects}\tprompts={plan.max_prompts_total}\t"
                    f"ai={plan.per_month_usages}"
                )
            return 0

        if args.list_users:
            users = list(
                db.execute(select(User).where(User.deleted.is_(False)).order_by(User.created_at.desc()).limit(50))
                .scalars()
                .all()
            )
            for user in users:
                label = user.phone or user.email or user.nick_name or "-"
                print(f"{user.id}\ttenant={user.tenant_id}\t{label}")
            return 0

        selectors = sum(1 for x in (args.user_id, args.phone, args.email) if x)
        if selectors != 1:
            raise SystemExit("Specify exactly one of --user-id / --phone / --email")
        if not args.plan:
            raise SystemExit("--plan is required")

        q = select(User).where(User.deleted.is_(False))
        if args.user_id:
            q = q.where(User.id == UUID(args.user_id))
        elif args.phone:
            q = q.where(User.phone == args.phone.strip())
        else:
            q = q.where(User.email == args.email.strip().lower())

        user = db.execute(q.limit(1)).scalar_one_or_none()
        if user is None:
            raise SystemExit("User not found")

        current = db.execute(
            select(TenantSubscription)
            .where(
                TenantSubscription.tenant_id == user.tenant_id,
                TenantSubscription.deleted.is_(False),
            )
            .limit(1)
        ).scalar_one_or_none()
        current_plan = db.get(Plan, current.plan_id) if current is not None else None

        preview = {
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "phone": user.phone,
            "email": user.email,
            "from_plan": current_plan.code if current_plan else None,
            "from_status": current.status if current else None,
            "to_plan": args.plan.strip().lower(),
            "to_cycle": args.cycle,
            "dry_run": bool(args.dry_run),
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))

        if args.dry_run:
            print("Dry-run only. Re-run without --dry-run to apply.", file=sys.stderr)
            return 0

        subscription = assign_subscription_plan(
            db,
            tenant_id=user.tenant_id,
            plan_code=args.plan,
            billing_cycle=args.cycle,
        )
        db.commit()
        plan = db.get(Plan, subscription.plan_id)
        result = {
            "ok": True,
            "subscription_id": str(subscription.id),
            "plan_code": plan.code if plan else args.plan,
            "plan_name": plan.name if plan else "",
            "billing_cycle": subscription.billing_cycle,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
