"""Doubao Web HTTP helpers (samantha protocol → SamplingChatResult fields)."""

from __future__ import annotations

from aperix_geo.services.providers.doubao_web.web_http.map_result import (
    map_sse_events_to_fields,
    map_web_http_to_sampling_result,
)
from aperix_geo.services.providers.doubao_web.web_http.protocol import (
    DEFAULT_BOT_ID,
    SAMANTHA_BASE_PARAMS,
    SAMANTHA_COMPLETION_URL,
    completion_body,
)

# client imports jobs.http — keep out of package __init__ to avoid cycles.
__all__ = [
    "DEFAULT_BOT_ID",
    "SAMANTHA_BASE_PARAMS",
    "SAMANTHA_COMPLETION_URL",
    "completion_body",
    "map_sse_events_to_fields",
    "map_web_http_to_sampling_result",
    "complete_web_http",
    "request_a_bogus",
]


def __getattr__(name: str):
    if name in {"complete_web_http", "request_a_bogus"}:
        from aperix_geo.services.providers.doubao_web.web_http import client

        return getattr(client, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
