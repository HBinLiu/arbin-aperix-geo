"""Display labels and API record-type mapping for quota ledger rows."""

from __future__ import annotations

from aperix_geo.db.models import TenantQuotaLedger
from aperix_geo.services.billing.constants import (
    API_RECORD_PACK_CONSUME,
    API_RECORD_SUBSCRIPTION_CONSUME,
    API_RECORD_SUBSCRIPTION_GRANT,
    API_RECORD_USAGE_PACK_PURCHASE,
    CONSUMED_FROM_PACK,
    CONSUMED_FROM_SUBSCRIPTION,
    LEDGER_RECORD_CONSUMPTION,
    LEDGER_RECORD_SUBSCRIPTION_GRANT,
    LEDGER_RECORD_USAGE_PACK_PURCHASE,
)
from aperix_geo.services.billing.usage_pack_catalog import format_usage_pack_order_label

_CONSUMPTION_SOURCE_LABELS = {
    "sampling": "自动采样",
    "retry": "重试请求",
    "setup": "品牌设置",
    "prompt": "提示词生成",
    "parse": "解析回复",
}

_SUBSCRIPTION_GRANT_SOURCE_LABELS = {
    "subscription": "订阅开通",
    "rollover": "周期发放",
}

_API_RECORD_TYPE_LABELS = {
    API_RECORD_USAGE_PACK_PURCHASE: "配额包",
    API_RECORD_SUBSCRIPTION_GRANT: "订阅发放",
    API_RECORD_SUBSCRIPTION_CONSUME: "订阅消耗",
    API_RECORD_PACK_CONSUME: "配额消耗",
}

API_RECORD_TYPE_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    (API_RECORD_SUBSCRIPTION_CONSUME, _API_RECORD_TYPE_LABELS[API_RECORD_SUBSCRIPTION_CONSUME]),
    (API_RECORD_PACK_CONSUME, _API_RECORD_TYPE_LABELS[API_RECORD_PACK_CONSUME]),
    (API_RECORD_USAGE_PACK_PURCHASE, _API_RECORD_TYPE_LABELS[API_RECORD_USAGE_PACK_PURCHASE]),
    (API_RECORD_SUBSCRIPTION_GRANT, _API_RECORD_TYPE_LABELS[API_RECORD_SUBSCRIPTION_GRANT]),
)


def consumption_source_label(source: str) -> str:
    return _CONSUMPTION_SOURCE_LABELS.get(source, source)


def usage_pack_product_label(product_code: str, *, quantity: int = 0) -> str:
    if not product_code:
        return "配额包购买"
    return format_usage_pack_order_label(product_code, quantity=quantity)


def quota_record_type_filter_options() -> list[tuple[str, str]]:
    return list(API_RECORD_TYPE_FILTER_OPTIONS)


def normalize_api_record_type_filter(value: str | None) -> str | None:
    if not value or value == "all":
        return None
    allowed = {option for option, _ in API_RECORD_TYPE_FILTER_OPTIONS}
    return value if value in allowed else None


def ledger_api_record_type_clauses(api_record_type: str) -> list:
    if api_record_type == API_RECORD_SUBSCRIPTION_CONSUME:
        return [
            TenantQuotaLedger.record_type == LEDGER_RECORD_CONSUMPTION,
            TenantQuotaLedger.consumed_from == CONSUMED_FROM_SUBSCRIPTION,
        ]
    if api_record_type == API_RECORD_PACK_CONSUME:
        return [
            TenantQuotaLedger.record_type == LEDGER_RECORD_CONSUMPTION,
            TenantQuotaLedger.consumed_from == CONSUMED_FROM_PACK,
        ]
    if api_record_type == API_RECORD_USAGE_PACK_PURCHASE:
        return [TenantQuotaLedger.record_type == LEDGER_RECORD_USAGE_PACK_PURCHASE]
    if api_record_type == API_RECORD_SUBSCRIPTION_GRANT:
        return [TenantQuotaLedger.record_type == LEDGER_RECORD_SUBSCRIPTION_GRANT]
    return []


def api_record_type_and_label(*, record_type: str, consumed_from: str) -> tuple[str, str]:
    if record_type == LEDGER_RECORD_USAGE_PACK_PURCHASE:
        return API_RECORD_USAGE_PACK_PURCHASE, _API_RECORD_TYPE_LABELS[API_RECORD_USAGE_PACK_PURCHASE]
    if record_type == LEDGER_RECORD_SUBSCRIPTION_GRANT:
        return API_RECORD_SUBSCRIPTION_GRANT, _API_RECORD_TYPE_LABELS[API_RECORD_SUBSCRIPTION_GRANT]
    if consumed_from == CONSUMED_FROM_SUBSCRIPTION:
        return API_RECORD_SUBSCRIPTION_CONSUME, _API_RECORD_TYPE_LABELS[API_RECORD_SUBSCRIPTION_CONSUME]
    return API_RECORD_PACK_CONSUME, _API_RECORD_TYPE_LABELS[API_RECORD_PACK_CONSUME]


def ledger_source_label(
    *,
    record_type: str,
    source: str,
    product_code: str = "",
    product_quantity: int = 0,
) -> str:
    if record_type == LEDGER_RECORD_USAGE_PACK_PURCHASE:
        return usage_pack_product_label(product_code, quantity=product_quantity)
    if record_type == LEDGER_RECORD_SUBSCRIPTION_GRANT:
        return _SUBSCRIPTION_GRANT_SOURCE_LABELS.get(source, source)
    return consumption_source_label(source)