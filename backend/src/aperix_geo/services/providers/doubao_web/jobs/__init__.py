"""Doubao geo-web-crawl job implementations (one module per mode).

Keep this package init import-light: handlers import ``jobs.<mode>`` modules
directly. Eager re-exports here would pull http/sign/share at package import
time and break lean Docker startup checks.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "build_crawl_payload",
    "build_probe_payload",
    "build_share_payload",
    "build_sign_payload",
    "build_web_http_payload",
    "run_doubao_browser_crawl_on_page",
    "run_doubao_login_probe_on_page",
    "run_doubao_share_on_page",
    "run_doubao_sign_on_page",
    "run_doubao_web_http_on_page",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "build_crawl_payload": (".crawl", "build_crawl_payload"),
    "run_doubao_browser_crawl_on_page": (".crawl", "run_doubao_browser_crawl_on_page"),
    "build_probe_payload": (".probe", "build_probe_payload"),
    "run_doubao_login_probe_on_page": (".probe", "run_doubao_login_probe_on_page"),
    "build_share_payload": (".share", "build_share_payload"),
    "run_doubao_share_on_page": (".share", "run_doubao_share_on_page"),
    "build_sign_payload": (".sign", "build_sign_payload"),
    "run_doubao_sign_on_page": (".sign", "run_doubao_sign_on_page"),
    "build_web_http_payload": (".http", "build_web_http_payload"),
    "run_doubao_web_http_on_page": (".http", "run_doubao_web_http_on_page"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    from importlib import import_module

    mod = import_module(module_name, __name__)
    value = getattr(mod, attr)
    globals()[name] = value
    return value
