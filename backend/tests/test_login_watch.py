"""Unit tests for geo-web-crawl login-complete heuristics."""

from __future__ import annotations

from aperix_geo.services.crawl_accounts.platforms import normalize_login_reason
from aperix_geo.services.crawl_browser import login_watch as w


def test_normalize_login_reason() -> None:
    assert normalize_login_reason("captcha") == "captcha"
    assert normalize_login_reason("LOGIN_EXPIRED") == "login_expired"
    assert normalize_login_reason("nope") == "login_expired"
    assert normalize_login_reason("") == "login_expired"


def test_login_reason_from_ticket_text() -> None:
    from aperix_geo.services.crawl_accounts.platforms import login_reason_from_ticket_text

    assert login_reason_from_ticket_text("auto:captcha: behavior captcha") == "captcha"
    assert (
        login_reason_from_ticket_text(
            "crawl_login: platform=doubao reason=captcha session=crawl-login:x"
        )
        == "captcha"
    )
    assert login_reason_from_ticket_text("auto:login_expired: redirected") == "login_expired"
    assert login_reason_from_ticket_text("") == "login_expired"


def test_ready_login_accepts_unchanged_session_cookies() -> None:
    """After captcha, jar often unchanged; still-logged-in must be able to close ticket."""
    baseline = (("sessionid", "same"),)
    assert not w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=baseline,
        baseline=baseline,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
        login_ui_visible=True,
    )
    assert w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=baseline,
        baseline=baseline,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
        login_ui_visible=False,
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
    assert not w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=baseline,
        baseline=baseline,
        captcha_visible=True,
        saw_captcha=True,
        grace_elapsed=True,
    )


def test_ready_login_empty_baseline() -> None:
    assert w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=(),
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=False,
    )


def test_ready_login_blocks_while_login_ui_visible() -> None:
    assert not w.ready_for_complete(
        reason="login_expired",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=(),
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
        login_ui_visible=True,
    )


def test_login_proof_ignores_guest_uid_tt() -> None:
    guest = {"cookies": [{"name": "uid_tt", "value": "x"}, {"name": "sid_tt", "value": "y"}]}
    assert w.session_cookie_names("doubao", guest) == ["sid_tt", "uid_tt"]
    assert w.login_proof_cookie_names("doubao", guest) == []
    logged = {"cookies": [{"name": "sessionid", "value": "s"}, {"name": "uid_tt", "value": "x"}]}
    assert w.login_proof_cookie_names("doubao", logged) == ["sessionid"]


def test_ready_captcha_requires_seen_then_clear_stable() -> None:
    assert not w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=True,
        saw_captcha=True,
        grace_elapsed=True,
        captcha_clear_stable=True,
    )
    # Grace alone must not complete (ops still solving / never saw captcha).
    assert not w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=False,
        grace_elapsed=True,
        captcha_clear_stable=False,
    )
    assert not w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=True,
        grace_elapsed=True,
        captcha_clear_stable=False,
    )
    assert w.ready_for_complete(
        reason="captcha",
        has_session=True,
        fingerprint=(("sessionid", "x"),),
        baseline=None,
        captcha_visible=False,
        saw_captcha=True,
        grace_elapsed=False,
        captcha_clear_stable=True,
    )


def test_baseline_fingerprint_ignores_guest_cookies() -> None:
    assert w.baseline_fingerprint(
        "doubao",
        {"cookies": [{"name": "odin_tt", "value": "guest"}]},
    ) == ()
    assert w.baseline_fingerprint(
        "doubao",
        {
            "cookies": [
                {"name": "sessionid", "value": "abc"},
                {"name": "sid_guard", "value": "g1"},
            ]
        },
    ) == (
        ("sessionid", "abc"),
        ("sid_guard", "g1"),
    )
