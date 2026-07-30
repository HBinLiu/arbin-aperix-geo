"""Alert message templates (email)."""

from __future__ import annotations

from aperix_geo.services.alerts.billing import ProviderBillingEvent

_ROLE_LABELS = {
    "analysis_llm": "内部分析 LLM",
    "sampling": "采样平台",
    "provider": "AI 平台",
}


def provider_display_name(provider_id: str) -> str:
    names = {
        "deepseek": "DeepSeek",
        "kimi": "Kimi",
        "doubao": "豆包",
        "qianwen": "通义千问",
        "yuanbao": "腾讯元宝",
        "ernie": "文心一言",
    }
    return names.get(provider_id, provider_id)


def billing_alert_email(event: ProviderBillingEvent, *, env: str) -> tuple[str, str]:
    name = provider_display_name(event.provider_id)
    role = _ROLE_LABELS.get(event.provider_role, event.provider_role)
    status = f"HTTP {event.status_code}" if event.status_code else "—"
    subject = f"[Aperix GEO] {name} 余额/额度异常 ({env})"
    body = "\n".join(
        [
            f"环境：{env}",
            f"平台：{name}（{role}）",
            f"类型：{'余额不足' if event.alert_kind == 'billing' else '额度耗尽'}",
            f"HTTP 状态：{status}",
            f"近 5 分钟内失败次数：{event.fail_count}",
            "",
            "错误摘要：",
            event.message,
            "",
            "建议：登录对应 AI 平台控制台检查余额并充值，或更新 API Key。",
            "充值完成前，相关采样/分析任务可能持续失败。",
        ]
    )
    return subject, body


def billing_recovery_email(provider_id: str, *, env: str) -> tuple[str, str]:
    name = provider_display_name(provider_id)
    subject = f"[Aperix GEO] {name} 已恢复 ({env})"
    body = f"环境：{env}\n平台：{name}\n\n该平台 API 调用已恢复正常。"
    return subject, body
