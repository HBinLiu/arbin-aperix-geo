"""Unit tests for geo-crawl-ops watch complete heuristics (import from docker/)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WATCH = _ROOT / "docker" / "geo-crawl-ops" / "watch_login.py"


def _load_watch():
    spec = importlib.util.spec_from_file_location("geo_crawl_ops_watch_login", _WATCH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ready_login_needs_cookie_change() -> None:
    w = _load_watch()
    baseline = (("sessionid", "old"),)
    assert not w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=baseline,
        baseline=baseline,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
    )
    assert w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=(("sessionid", "new"),),
        baseline=baseline,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
    )


def test_ready_login_empty_baseline() -> None:
    w = _load_watch()
    assert w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=(),
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=False,
    )


def test_ready_captcha_requires_gone() -> None:
    w = _load_watch()
    assert not w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=True,
        saw_captcha=True,
        grace_elapsed=True,
    )
    assert w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=True,
        grace_elapsed=False,
    )
    # Never saw captcha: only after grace
    assert not w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=False,
    )
    assert w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
    )
