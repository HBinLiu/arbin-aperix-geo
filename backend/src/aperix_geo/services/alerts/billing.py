"""Classify provider errors as billing / quota exhaustion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

BillingAlertKind = Literal["billing", "quota"]

BILLING_HTTP_STATUSES = frozenset({402})

_BILLING_MESSAGE_RE = re.compile(
    r"insufficient\s+balance"
    r"|insufficient_quota"
    r"|exceeded_current_quota"
    r"|余额不足"
    r"|额度不足"
    r"|账户余额"
    r"|recharge your account"
    r"|is suspended due to insufficient"
    r"|account.*suspended",
    re.IGNORECASE,
)

_PROVIDER_PREFIX_RE = re.compile(
    r"^([A-Za-z\u4e00-\u9fff]+)\s+(?:HTTP|timeout|API|error)",
    re.IGNORECASE,
)

_LABEL_TO_ID: dict[str, str] = {
    "deepseek": "deepseek",
    "kimi": "kimi",
    "doubao": "doubao",
    "qianwen": "qianwen",
    "yuanbao": "yuanbao",
    "ernie": "ernie",
    "豆包": "doubao",
    "通义千问": "qianwen",
    "腾讯元宝": "yuanbao",
    "文心一言": "ernie",
}


@dataclass(frozen=True)
class ProviderBillingEvent:
    provider_id: str
    provider_role: str
    alert_kind: BillingAlertKind
    status_code: int | None
    message: str
    fail_count: int


def is_billing_provider_error(message: str, status_code: int | None = None) -> bool:
    """True when the failure indicates insufficient balance / quota, not transient 429."""
    if status_code in BILLING_HTTP_STATUSES:
        return True
    if _BILLING_MESSAGE_RE.search(message or ""):
        return True
    return False


def classify_billing_error(
    message: str,
    *,
    status_code: int | None = None,
    provider_id: str | None = None,
    provider_role: str = "provider",
    fail_count: int = 1,
) -> ProviderBillingEvent | None:
    if not is_billing_provider_error(message, status_code):
        return None
    resolved_id = provider_id or provider_id_from_message(message)
    kind: BillingAlertKind = "quota" if status_code == 429 else "billing"
    return ProviderBillingEvent(
        provider_id=resolved_id,
        provider_role=provider_role,
        alert_kind=kind,
        status_code=status_code,
        message=(message or "")[:500],
        fail_count=fail_count,
    )


def provider_id_from_message(message: str) -> str:
    match = _PROVIDER_PREFIX_RE.match((message or "").strip())
    if not match:
        return "unknown"
    label = match.group(1).strip().lower()
    return _LABEL_TO_ID.get(label, label)


def infer_provider_role(provider_id: str) -> str:
    if provider_id == "deepseek":
        return "analysis_llm"
    if provider_id in {"doubao", "kimi", "qianwen", "yuanbao", "ernie"}:
        return "sampling"
    return "provider"
