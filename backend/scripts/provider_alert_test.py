#!/usr/bin/env python3
"""运维：测试 PROVIDER_ALERT / SMTP 发信（豆包工单邮件同通道）。

用法
----
  cd backend && export PYTHONPATH=src
  ./.venv/bin/python scripts/provider_alert_test.py
  ./.venv/bin/python scripts/provider_alert_test.py --to you@example.com
  ./.venv/bin/python scripts/provider_alert_test.py --reset-cooldown --account-id <uuid>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="测试运维告警邮件（SMTP）")
    parser.add_argument("--to", default="", help="覆盖 PROVIDER_ALERT_EMAIL_TO（逗号分隔）")
    parser.add_argument(
        "--reset-cooldown",
        action="store_true",
        help="清除 doubao_account:{account-id} 的告警冷却（需 --account-id）",
    )
    parser.add_argument("--account-id", default="", help="与 --reset-cooldown 联用")
    args = parser.parse_args()

    from aperix_geo.config import get_settings, resolve_settings_env_mode
    from aperix_geo.services.alerts.email import send_alert_email
    from aperix_geo.services.mail.smtp import smtp_configured
    from aperix_geo.utils.cache.redis_kv import shared_redis_client

    settings = get_settings()
    mode = resolve_settings_env_mode()
    print(f"settings_mode={mode} env_field={settings.env!r}")
    print(f"provider_alert_enabled={settings.provider_alert_enabled}")
    print(f"provider_alert_email_to={settings.provider_alert_email_to!r}")
    print(f"provider_alert_cooldown_s={settings.provider_alert_cooldown_seconds}")
    print(
        f"smtp_host={settings.smtp_host!r} port={settings.smtp_port} "
        f"use_tls={settings.smtp_use_tls} user={settings.smtp_user!r} "
        f"from={settings.smtp_from!r} configured={smtp_configured(settings)}"
    )

    if args.reset_cooldown:
        if not args.account_id.strip():
            print("--reset-cooldown 需要 --account-id", file=sys.stderr)
            return 1
        account_id = UUID(args.account_id.strip())
        gate_id = f"doubao_account:{account_id}"
        client = shared_redis_client()
        if client is None:
            print("Redis 不可用，无法清冷却", file=sys.stderr)
            return 1
        keys = [
            f"aperix:provider_alert:v1:{gate_id}:state",
            f"aperix:provider_alert:v1:{gate_id}:last_sent",
            f"aperix:provider_alert:v1:fail:{gate_id}",
        ]
        n = int(client.delete(*keys))
        print(f"cleared_cooldown keys_deleted={n} gate={gate_id}")
        return 0

    to_addrs = [
        p.strip()
        for p in (args.to or settings.provider_alert_email_to or "").split(",")
        if p.strip()
    ]
    if not settings.provider_alert_enabled and not args.to:
        print(
            "PROVIDER_ALERT_ENABLED=false；仍可加 --to 强制试发一封",
            file=sys.stderr,
        )
    if not to_addrs:
        print("无收件人：配置 PROVIDER_ALERT_EMAIL_TO 或传 --to", file=sys.stderr)
        return 1
    if not smtp_configured(settings):
        print("SMTP 未配齐（SMTP_HOST / FROM|USER）", file=sys.stderr)
        return 1

    try:
        send_alert_email(
            settings,
            to_addrs=to_addrs,
            subject=f"[Aperix GEO] SMTP 测试 ({settings.env})",
            body=(
                "这是一封运维告警通道测试邮件。\n"
                f"settings_mode={mode}\n"
                "若能收到，说明豆包工单邮件通道可用"
                "（仍可能被 6h 冷却挡住真实开票告警，可用 --reset-cooldown）。\n"
            ),
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print(f"OK: sent to {to_addrs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
