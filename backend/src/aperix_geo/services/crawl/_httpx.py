"""Thread-local httpx client with connection pooling."""

from __future__ import annotations

import threading

import httpx

from aperix_geo.utils.http import HTML_FETCH_HEADERS, ICON_FETCH_HEADERS

_local = threading.local()


def _thread_local_client(*, attr: str, headers: dict[str, str]) -> httpx.Client:
    client = getattr(_local, attr, None)
    if client is None or client.is_closed:
        setattr(
            _local,
            attr,
            httpx.Client(
                headers=headers,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
            ),
        )
    return getattr(_local, attr)


def get_httpx_client() -> httpx.Client:
    return _thread_local_client(attr="client", headers=HTML_FETCH_HEADERS)


def get_icon_httpx_client() -> httpx.Client:
    return _thread_local_client(attr="icon_client", headers=ICON_FETCH_HEADERS)
