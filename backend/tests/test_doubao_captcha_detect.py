"""Tests for Doubao behavior-captcha detection (frames + structure)."""

from __future__ import annotations

from types import SimpleNamespace

from aperix_geo.services.providers.doubao_web.captcha import (
    _iframe_attrs_look_like_captcha,
    page_shows_behavior_captcha,
)
from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha


def test_page_looks_like_captcha_phrases() -> None:
    assert page_looks_like_captcha("请拖动滑块完成验证")
    assert page_looks_like_captcha("拖动到指定位置")
    assert not page_looks_like_captcha("界面支持拖动排序，不影响结论")


class _FakeLocator:
    def __init__(self, *, text: str = "", visible: bool = False, attrs: dict | None = None, count: int = 0):
        self._text = text
        self._visible = visible
        self._attrs = attrs or {}
        self._count = count

    def inner_text(self, timeout: int = 0) -> str:
        return self._text

    def count(self) -> int:
        return self._count

    def nth(self, _i: int) -> _FakeLocator:
        return self

    def is_visible(self) -> bool:
        return self._visible

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)


def test_page_shows_captcha_from_child_frame_text() -> None:
    main_body = _FakeLocator(text="正常聊天内容")
    frame_body = _FakeLocator(text="请拖动滑块完成验证")

    def main_locator(sel: str) -> _FakeLocator:
        if sel == "body":
            return main_body
        if sel == "iframe":
            return _FakeLocator(count=0)
        return _FakeLocator(count=0)

    def frame_locator(sel: str) -> _FakeLocator:
        if sel == "body":
            return frame_body
        return _FakeLocator(count=0)

    child = SimpleNamespace(locator=frame_locator)
    page = SimpleNamespace(
        locator=main_locator,
        main_frame=object(),
        frames=[child],
    )
    assert page_shows_behavior_captcha(page) is True


def test_page_shows_captcha_from_iframe_src() -> None:
    iframe = _FakeLocator(
        visible=True,
        count=1,
        attrs={"src": "https://example.com/captcha/slide?x=1", "id": "captcha-frame"},
    )

    def locator(sel: str) -> _FakeLocator:
        if sel == "body":
            return _FakeLocator(text="正常页面")
        if sel == "iframe":
            return iframe
        return _FakeLocator(count=0)

    page = SimpleNamespace(locator=locator, main_frame=None, frames=[])
    assert _iframe_attrs_look_like_captcha(page) is True
    assert page_shows_behavior_captcha(page) is True


def test_iframe_verify_alone_not_captcha() -> None:
    """Bare verify/slide in analytics iframes must not abort sampling after send."""
    iframe = _FakeLocator(
        visible=True,
        count=1,
        attrs={"src": "https://cdn.example.com/sdk/verify.js", "id": "sec-slide"},
    )

    def locator(sel: str) -> _FakeLocator:
        if sel == "body":
            return _FakeLocator(text="正在生成回答")
        if sel == "iframe":
            return iframe
        return _FakeLocator(count=0)

    page = SimpleNamespace(locator=locator, main_frame=None, frames=[])
    assert _iframe_attrs_look_like_captcha(page) is False
    assert page_shows_behavior_captcha(page) is False


def test_page_shows_captcha_false_on_normal_chat() -> None:
    body = _FakeLocator(text="适合小团队的 CRM 有哪些")

    def locator(sel: str) -> _FakeLocator:
        if sel == "body":
            return body
        return _FakeLocator(count=0)

    page = SimpleNamespace(locator=locator, main_frame=None, frames=[])
    assert page_shows_behavior_captcha(page) is False
