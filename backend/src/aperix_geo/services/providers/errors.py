"""Provider exception hierarchy."""

from __future__ import annotations

import re

TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
_HTTP_STATUS_RE = re.compile(r"\bhttp\s+(\d{3})\b", re.IGNORECASE)


class ProviderError(Exception):
    """Base for sampling provider failures."""

    status_code: int | None
    retryable: bool | None

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def is_transient_http_status(status: int | None) -> bool:
    return status in TRANSIENT_HTTP_STATUSES if status is not None else False


def parse_http_status_from_message(message: str) -> int | None:
    match = _HTTP_STATUS_RE.search(message)
    return int(match.group(1)) if match else None


def raise_provider_error(
    cls: type[ProviderError],
    message: str,
    *,
    status_code: int | None = None,
    retryable: bool | None = None,
    cause: BaseException | None = None,
    provider_id: str | None = None,
    provider_role: str | None = None,
) -> None:
    """Raise a ProviderError with optional HTTP status and retry hint."""
    from aperix_geo.services.alerts.billing import is_billing_provider_error
    from aperix_geo.services.alerts.dispatch import maybe_report_provider_billing_alert

    if is_billing_provider_error(message, status_code):
        retryable = False
        maybe_report_provider_billing_alert(
            message,
            status_code=status_code,
            provider_id=provider_id,
            provider_role=provider_role,
        )
    if retryable is None and status_code is not None:
        retryable = is_transient_http_status(status_code)
    raise cls(message, status_code=status_code, retryable=retryable) from cause


class LLMProviderError(ProviderError):
    """Internal DeepSeek chat_completion failures."""


class DoubaoProviderError(ProviderError):
    pass


class QianwenProviderError(ProviderError):
    pass


class YuanbaoProviderError(ProviderError):
    pass


class ErnieProviderError(ProviderError):
    pass


class DeepseekProviderError(ProviderError):
    pass


class KimiProviderError(ProviderError):
    pass
