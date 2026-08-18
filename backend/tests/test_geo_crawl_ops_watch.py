"""Unit tests for geo-crawl-ops watch complete heuristics (import from docker/)."""

from __future__ import annotations

import importlib.util
import json
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


def test_ready_login_blocks_while_login_ui_visible() -> None:
    w = _load_watch()
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
    w = _load_watch()
    guest = {"cookies": [{"name": "uid_tt", "value": "x"}, {"name": "sid_tt", "value": "y"}]}
    assert w.session_cookie_names("doubao", guest) == ["sid_tt", "uid_tt"]
    assert w.login_proof_cookie_names("doubao", guest) == []
    logged = {"cookies": [{"name": "sessionid", "value": "s"}, {"name": "uid_tt", "value": "x"}]}
    assert w.login_proof_cookie_names("doubao", logged) == ["sessionid"]


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


def test_load_login_baseline_empty_or_missing(tmp_path: Path) -> None:
    w = _load_watch()
    assert w.load_login_baseline("doubao", "") == ()
    assert w.load_login_baseline("doubao", str(tmp_path / "missing.json")) == ()
    empty = tmp_path / "empty.json"
    empty.write_text('{"cookies":[{"name":"odin_tt","value":"guest"}]}', encoding="utf-8")
    assert w.load_login_baseline("doubao", str(empty)) == ()


def test_load_login_baseline_from_session_cookies(tmp_path: Path) -> None:
    w = _load_watch()
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "sessionid", "value": "abc"},
                    {"name": "sid_guard", "value": "g1"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert w.load_login_baseline("doubao", str(path)) == (
        ("sessionid", "abc"),
        ("sid_guard", "g1"),
    )


def test_pick_best_context_prefers_session_cookies() -> None:
    w = _load_watch()

    class Ctx:
        def __init__(self, cookies, pages=None):
            self._cookies = cookies
            self.pages = pages or []

        def storage_state(self):
            return {"cookies": self._cookies}

    class Browser:
        def __init__(self, contexts):
            self.contexts = contexts

    empty = Ctx([{"name": "odin_tt", "value": "guest"}])
    logged_in = Ctx(
        [
            {"name": "sessionid", "value": "live"},
            {"name": "sid_guard", "value": "g"},
        ],
        pages=["p1"],
    )
    browser = Browser([empty, logged_in])
    ctx, state, names, fp = w.pick_best_context_state(browser, "doubao")
    assert ctx is logged_in
    assert "sessionid" in names
    assert ("sessionid", "live") in fp
    assert any(c.get("name") == "sessionid" for c in state["cookies"])


def test_resolve_storage_state_prefers_live_dump(tmp_path: Path, monkeypatch) -> None:
    w = _load_watch()
    live = tmp_path / "live.json"
    live.write_text(
        json.dumps({"cookies": [{"name": "sessionid", "value": "from-live"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(w, "LIVE_STATE_PATH", live)

    class Ctx:
        pages = []

        def storage_state(self):
            return {"cookies": []}

    class Browser:
        contexts = [Ctx()]

    ctx, state, names, fp, src = w.resolve_storage_state(Browser(), "doubao")
    assert src == "live"
    assert names == ["sessionid"]
    assert fp == (("sessionid", "from-live"),)
    assert state["cookies"][0]["value"] == "from-live"


