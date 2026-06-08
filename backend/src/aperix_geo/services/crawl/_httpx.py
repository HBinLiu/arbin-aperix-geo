"""Thread-local httpx client with connection pooling."""

from __future__ import annotations

import threading

import httpx

from aperix_geo.utils.http import HTML_FETCH_HEADERS

_local = threading.local()


def get_httpx_client() -> httpx.Client:
    client = getattr(_local, "client", None)
    if client is None or client.is_closed:
        _local.client = httpx.Client(
            headers=HTML_FETCH_HEADERS,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
        )
    return _local.client
