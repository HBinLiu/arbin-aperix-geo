"""Landing /chat must switch off「工作」before composing."""

from __future__ import annotations

from unittest.mock import MagicMock

from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.ui_flow import (
    _ensure_chat_mode,
    _open_fresh_chat,
)


class _Tab:
    def __init__(self, *, visible: bool = True, clicks: list[str] | None = None, name: str = "") -> None:
        self.visible = visible
        self.clicks = clicks if clicks is not None else []
        self.name = name
        self.first = self

    def count(self) -> int:
        return 1 if self.visible else 0

    def wait_for(self, **_k) -> None:
        if not self.visible:
            raise TimeoutError("not visible")

    def click(self, timeout: int = 0) -> None:
        self.clicks.append(self.name)


class _Page:
    def __init__(self, *, show_toggle: bool = True, url: str = "https://www.doubao.com/chat/") -> None:
        self.url = url
        self.clicks: list[str] = []
        self.work = _Tab(visible=show_toggle, clicks=self.clicks, name="工作")
        self.chat = _Tab(visible=show_toggle, clicks=self.clicks, name="对话")
        self.waits = 0
        self.gotos: list[str] = []

    def get_by_role(self, role: str, name=None) -> _Tab | MagicMock:
        if role != "button":
            empty = MagicMock()
            empty.count.return_value = 0
            return empty
        pattern = getattr(name, "pattern", str(name or ""))
        if pattern == sel.WORK_TAB_NAME.pattern:
            return self.work
        if pattern == sel.CHAT_TAB_NAME.pattern:
            return self.chat
        empty = MagicMock()
        empty.count.return_value = 0
        empty.first = empty
        return empty

    def locator(self, *_a, **_k) -> MagicMock:
        empty = MagicMock()
        empty.count.return_value = 0
        return empty

    def get_by_text(self, *_a, **_k) -> MagicMock:
        empty = MagicMock()
        empty.count.return_value = 0
        return empty

    def wait_for_timeout(self, _ms: int) -> None:
        self.waits += 1

    def goto(self, url: str, **_k) -> None:
        self.gotos.append(url)
        self.url = url


def test_chat_tab_regex_is_exact() -> None:
    assert sel.CHAT_TAB_NAME.search("对话")
    assert not sel.CHAT_TAB_NAME.search("新对话")
    assert not sel.CHAT_TAB_NAME.search("对话记录")
    assert sel.WORK_TAB_NAME.search("工作")
    assert not sel.WORK_TAB_NAME.search("工作台")


def test_ensure_chat_mode_clicks_对话_when_工作_toggle_present() -> None:
    page = _Page(show_toggle=True)
    _ensure_chat_mode(page)
    assert page.clicks == ["对话"]


def test_ensure_chat_mode_skips_when_toggle_absent() -> None:
    page = _Page(show_toggle=False)
    _ensure_chat_mode(page)
    assert page.clicks == []


def test_open_fresh_chat_clicks_对话_on_blank_landing() -> None:
    page = _Page(show_toggle=True, url="https://www.doubao.com/chat/")
    _open_fresh_chat(page, base_url="https://www.doubao.com/chat/", click_new_chat=False)
    assert page.clicks == ["对话"]
    assert page.gotos == []
