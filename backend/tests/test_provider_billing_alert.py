"""Tests for provider billing alert classification and retry policy."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.alerts.billing import (
    classify_billing_error,
    is_billing_provider_error,
    provider_id_from_message,
)
from aperix_geo.services.alerts.state import evaluate_alert_gate, mark_alert_sent
from aperix_geo.services.providers.errors import LLMProviderError, raise_provider_error
from aperix_geo.services.sampling.llm import SamplingLLMError
from aperix_geo.services.sampling.retry_policy import is_retryable_sampling_error


def test_is_billing_provider_error_deepseek_402() -> None:
    msg = "DeepSeek HTTP 402: Insufficient Balance"
    assert is_billing_provider_error(msg, 402)


def test_is_billing_provider_error_kimi_429_with_balance_message() -> None:
    msg = (
        "Kimi HTTP 429: Error code: 429 - {'error': {'message': "
        "'Your account is suspended due to insufficient balance'}}"
    )
    assert is_billing_provider_error(msg, 429)


def test_is_not_billing_plain_429() -> None:
    assert not is_billing_provider_error("Doubao HTTP 429: too many requests", 429)


def test_provider_id_from_message() -> None:
    assert provider_id_from_message("Kimi HTTP 429: ...") == "kimi"
    assert provider_id_from_message("DeepSeek HTTP 402: ...") == "deepseek"


def test_classify_billing_error() -> None:
    event = classify_billing_error(
        "Kimi HTTP 429: insufficient balance",
        status_code=429,
        provider_id="kimi",
        provider_role="sampling",
        fail_count=5,
    )
    assert event is not None
    assert event.provider_id == "kimi"
    assert event.alert_kind == "quota"


def test_billing_errors_not_retryable() -> None:
    exc = SamplingLLMError(
        "Kimi HTTP 429: suspended due to insufficient balance",
        status_code=429,
    )
    assert not is_retryable_sampling_error(exc)


def test_raise_provider_error_marks_billing_non_retryable() -> None:
    with patch("aperix_geo.services.alerts.dispatch.maybe_report_provider_billing_alert") as report:
        try:
            raise_provider_error(
                LLMProviderError,
                "DeepSeek HTTP 402: Insufficient Balance",
                status_code=402,
                provider_id="deepseek",
                provider_role="analysis_llm",
            )
        except LLMProviderError as exc:
            assert exc.retryable is False
            report.assert_called_once()


def test_evaluate_alert_gate_respects_min_fails(monkeypatch) -> None:
    calls: list[int] = []

    def fake_incr(_provider_id: str) -> int:
        calls.append(1)
        return len(calls)

    monkeypatch.setattr("aperix_geo.services.alerts.state.increment_billing_fail", fake_incr)
    monkeypatch.setattr("aperix_geo.services.alerts.state.shared_redis_client", lambda: None)

    first = evaluate_alert_gate("kimi", min_fails=3, cooldown_seconds=3600)
    second = evaluate_alert_gate("kimi", min_fails=3, cooldown_seconds=3600)
    third = evaluate_alert_gate("kimi", min_fails=3, cooldown_seconds=3600)

    assert not first.should_notify
    assert not second.should_notify
    assert third.should_notify
    assert third.fail_count == 3


def test_mark_alert_sent_blocks_until_cooldown(monkeypatch) -> None:
    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key: str) -> str | None:
            return store.get(key)

        def set(self, key: str, value: str) -> None:
            store[key] = value

        def pipeline(self):
            return self

        def execute(self):
            return None

        def delete(self, key: str) -> None:
            store.pop(key, None)

        def incr(self, key: str) -> int:
            store[key] = str(int(store.get(key, "0")) + 1)
            return int(store[key])

        def expire(self, key: str, _ttl: int) -> None:
            return None

    fake = FakeRedis()
    monkeypatch.setattr("aperix_geo.services.alerts.state.shared_redis_client", lambda: fake)
    monkeypatch.setattr("aperix_geo.services.alerts.state.increment_billing_fail", lambda _pid: 5)

    mark_alert_sent("kimi")
    gated = evaluate_alert_gate("kimi", min_fails=1, cooldown_seconds=3600)
    assert not gated.should_notify
