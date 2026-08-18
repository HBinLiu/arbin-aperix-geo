"""Landing /chat must switch off「工作」and recover from「系统异常」."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError
from aperix_geo.services.providers.doubao_web.runtime import (
    _composer,
    ensure_chat_mode,
    page_has_system_error,
    wait_until_logged_in,
)
from aperix_geo.services.providers.doubao_web.ui_flow import _open_fresh_chat


class _Tab:
    def __init__(
        self,
        *,
        visible: bool = True,
        clicks: list[str] | None = None,
        name: str = "",
        css_class: str = "",
    ) -> None:
        self.visible = visible
        self.clicks = clicks if clicks is not None else []
        self.name = name
        self.css_class = css_class
        self.first = self

    def count(self) -> int:
        return 1 if self.visible else 0

    def wait_for(self, **_k) -> None:
        if not self.visible:
            raise TimeoutError("not visible")

    def click(self, timeout: int = 0) -> None:
        self.clicks.append(self.name)

    def get_attribute(self, name: str) -> str:
        if name == "class":
            return self.css_class
        return ""

    def is_visible(self) -> bool:
        return self.visible

    def nth(self, _i: int) -> "_Tab":
        return self


class _Page:
    def __init__(
        self,
        *,
        show_toggle: bool = True,
        chat_selected: bool = False,
        url: str = "https://www.doubao.com/chat/",
        work_heading: bool = False,
    ) -> None:
        self.url = url
        self.clicks: list[str] = []
        chat_cls = (
            "text-dbx-text-primary" if chat_selected else "text-dbx-text-secondary"
        )
        work_cls = (
            "text-dbx-text-secondary" if chat_selected else "text-dbx-text-primary"
        )
        self.work = _Tab(
            visible=show_toggle, clicks=self.clicks, name="工作", css_class=work_cls
        )
        self.chat = _Tab(
            visible=show_toggle, clicks=self.clicks, name="对话", css_class=chat_cls
        )
        self.work_heading = work_heading
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
        empty.nth.return_value.is_visible.return_value = False
        return empty

    def get_by_text(self, name=None) -> MagicMock:
        empty = MagicMock()
        pattern = getattr(name, "pattern", str(name or ""))
        hit = self.work_heading and pattern == sel.WORK_LANDING_HINT.pattern
        empty.count.return_value = 1 if hit else 0
        empty.nth.return_value.is_visible.return_value = bool(hit)
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
    assert sel.WORK_LANDING_HINT.search("今天有什么工作要处理？")
    assert sel.SYSTEM_ERROR_HINT.search("系统异常")


def test_ensure_chat_mode_clicks_对话_when_unselected() -> None:
    page = _Page(show_toggle=True, chat_selected=False)
    assert ensure_chat_mode(page) is True
    assert page.clicks == ["对话"]


def test_ensure_chat_mode_skips_when_对话_already_selected() -> None:
    page = _Page(show_toggle=True, chat_selected=True)
    assert ensure_chat_mode(page) is False
    assert page.clicks == []


def test_ensure_chat_mode_skips_when_toggle_absent() -> None:
    page = _Page(show_toggle=False)
    assert ensure_chat_mode(page) is False
    assert page.clicks == []


def test_ensure_chat_mode_clicks_when_work_heading_visible() -> None:
    page = _Page(show_toggle=True, chat_selected=True, work_heading=True)
    assert ensure_chat_mode(page) is True
    assert page.clicks == ["对话"]


def test_open_fresh_chat_clicks_对话_on_blank_landing() -> None:
    page = _Page(show_toggle=True, chat_selected=False, url="https://www.doubao.com/chat/")
    _open_fresh_chat(page, base_url="https://www.doubao.com/chat/", click_new_chat=False)
    assert page.clicks == ["对话"]
    assert page.gotos == []


def test_hidden_composer_is_ignored() -> None:
    class Hidden:
        def is_visible(self) -> bool:
            return False

    class Loc:
        def count(self) -> int:
            return 1

        def nth(self, _i: int) -> Hidden:
            return Hidden()

    class Page:
        def locator(self, _css: str) -> Loc:
            return Loc()

        def get_by_role(self, *_a, **_k) -> Loc:
            return Loc()

    assert _composer(Page()) is None


def test_page_has_system_error() -> None:
    class Body:
        def inner_text(self, timeout: int = 0) -> str:
            return "操作失败，系统异常，请稍后重试"

    class Page:
        def locator(self, css: str) -> Body:
            assert css == "body"
            return Body()

    assert page_has_system_error(Page()) is True


def test_wait_until_logged_in_reloads_on_系统异常() -> None:
    class Body:
        def __init__(self, page: "ErrPage") -> None:
            self.page = page

        def inner_text(self, timeout: int = 0) -> str:
            return self.page.body

    class ErrPage:
        url = "https://www.doubao.com/chat/"
        body = "系统异常"
        gotos: list[str] = []

        def locator(self, css: str) -> Body | MagicMock:
            if css == "body":
                return Body(self)
            empty = MagicMock()
            empty.count.return_value = 0
            return empty

        def goto(self, url: str, **_k) -> None:
            self.gotos.append(url)
            self.body = ""

        def wait_for_timeout(self, *_a, **_k) -> None:
            return None

        def get_by_role(self, *_a, **_k) -> MagicMock:
            empty = MagicMock()
            empty.count.return_value = 0
            empty.first.wait_for.side_effect = TimeoutError("missing")
            return empty

        def get_by_text(self, *_a, **_k) -> MagicMock:
            empty = MagicMock()
            empty.count.return_value = 0
            return empty

    page = ErrPage()
    with patch(
        "aperix_geo.services.providers.doubao_web.runtime.assert_logged_in",
        side_effect=[DoubaoCrawlError("chat UI not ready", session_alive=True), None],
    ):
        wait_until_logged_in(page, timeout_s=2.0)
    assert page.gotos == ["https://www.doubao.com/chat/"]
