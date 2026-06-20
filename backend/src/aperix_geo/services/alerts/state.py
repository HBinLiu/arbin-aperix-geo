"""Redis-backed cooldown / fail counting for provider billing alerts."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from aperix_geo.utils.cache.redis_kv import shared_redis_client

AlertState = Literal["open", "resolved"]

_FAIL_WINDOW_S = 300
_STATE_PREFIX = "aperix:provider_alert:v1"
_FAIL_PREFIX = f"{_STATE_PREFIX}:fail"
_STATE_KEY = f"{_STATE_PREFIX}:{{provider_id}}:state"
_LAST_SENT_KEY = f"{_STATE_PREFIX}:{{provider_id}}:last_sent"


@dataclass(frozen=True)
class AlertGateResult:
    should_notify: bool
    fail_count: int
    state: AlertState


def _fail_key(provider_id: str) -> str:
    return f"{_FAIL_PREFIX}:{provider_id}"


def _state_key(provider_id: str) -> str:
    return _STATE_KEY.format(provider_id=provider_id)


def _last_sent_key(provider_id: str) -> str:
    return _LAST_SENT_KEY.format(provider_id=provider_id)


def increment_billing_fail(provider_id: str) -> int:
    client = shared_redis_client()
    if client is None:
        return 1
    key = _fail_key(provider_id)
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, _FAIL_WINDOW_S)
        return count
    except Exception:
        return 1


def evaluate_alert_gate(
    provider_id: str,
    *,
    min_fails: int,
    cooldown_seconds: int,
) -> AlertGateResult:
    fail_count = increment_billing_fail(provider_id)
    if fail_count < min_fails:
        return AlertGateResult(should_notify=False, fail_count=fail_count, state="resolved")

    client = shared_redis_client()
    if client is None:
        return AlertGateResult(should_notify=True, fail_count=fail_count, state="resolved")

    try:
        state_raw = client.get(_state_key(provider_id)) or "resolved"
        state: AlertState = "open" if state_raw == "open" else "resolved"
        if state == "open":
            last_sent_raw = client.get(_last_sent_key(provider_id))
            if last_sent_raw:
                elapsed = time.time() - float(last_sent_raw)
                if elapsed < cooldown_seconds:
                    return AlertGateResult(should_notify=False, fail_count=fail_count, state=state)
        return AlertGateResult(should_notify=True, fail_count=fail_count, state=state)
    except Exception:
        return AlertGateResult(should_notify=True, fail_count=fail_count, state="resolved")


def mark_alert_sent(provider_id: str) -> None:
    client = shared_redis_client()
    if client is None:
        return
    now = str(time.time())
    try:
        pipe = client.pipeline()
        pipe.set(_state_key(provider_id), "open")
        pipe.set(_last_sent_key(provider_id), now)
        pipe.execute()
    except Exception:
        return


def mark_provider_recovered(provider_id: str) -> bool:
    """Return True if provider was previously in open alert state."""
    client = shared_redis_client()
    if client is None:
        return False
    try:
        was_open = client.get(_state_key(provider_id)) == "open"
        if was_open:
            pipe = client.pipeline()
            pipe.set(_state_key(provider_id), "resolved")
            pipe.delete(_fail_key(provider_id))
            pipe.execute()
        return was_open
    except Exception:
        return False
