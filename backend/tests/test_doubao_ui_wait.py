"""Wait-for-reply must not treat the user-message toolbar as generation end."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError
from aperix_geo.services.providers.doubao_web.ui_flow import (
    _extract_assistant_text,
    _extract_search_panel,
    _human_pause,
    _last_assistant_md_text,
    _wait_generation_done,
    _wait_until,
)


class _Box:
    def __init__(self, text: str) -> None:
        self._text = text

    def is_visible(self) -> bool:
        return True

    def bounding_box(self) -> dict[str, float]:
        return {"x": 400.0, "y": 200.0, "width": 600.0, "height": 80.0}

    def inner_text(self, timeout: int = 0) -> str:
        return self._text


class _Boxes:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts

    def count(self) -> int:
        return len(self._texts)

    def nth(self, i: int) -> _Box:
        return _Box(self._texts[i])

    @property
    def last(self) -> _Box:
        return _Box(self._texts[-1] if self._texts else "")


class _Page:
    def __init__(self) -> None:
        self.url = "https://www.doubao.com/chat/thread1"
        self.stop = False
        self.streaming = False
        self.md_texts: list[str] = []
        self.body = "shell"
        self.waits = 0

    def locator(self, css: str) -> _Boxes | MagicMock:
        if css == ".md-box-root":
            return _Boxes(self.md_texts)
        if css == "body":
            body = MagicMock()
            body.inner_text.return_value = self.body
            return body
        return MagicMock(count=lambda: 0)

    def wait_for_timeout(self, _ms: int) -> None:
        self.waits += 1
        if self.waits == 2 and not self.md_texts:
            self.md_texts = ["助手正文"]
            self.stop = False
            self.streaming = False

    def inner_text(self, _sel: str) -> str:
        return self.body

    def evaluate(self, *_a, **_k) -> str:
        return ""

    def get_by_role(self, *_a, **_k) -> MagicMock:
        empty = MagicMock()
        empty.count.return_value = 0
        return empty


def test_human_pause_uses_inclusive_random_range() -> None:
    page = MagicMock()
    with patch(
        "aperix_geo.services.providers.doubao_web.ui_flow.random.randint",
        return_value=317,
    ) as randint:
        ms = _human_pause(page)
    randint.assert_called_once_with(250, 500)
    assert ms == 317
    page.wait_for_timeout.assert_called_once_with(317)


def test_human_pause_ceiling_caps_upper_bound() -> None:
    page = MagicMock()
    with patch(
        "aperix_geo.services.providers.doubao_web.ui_flow.random.randint",
        return_value=120,
    ) as randint:
        ms = _human_pause(page, ceiling_ms=180)
    randint.assert_called_once_with(180, 180)
    assert ms == 120


def test_wait_until_fails_fast_on_system_error() -> None:
    class Body:
        def inner_text(self, timeout: int = 0) -> str:
            return "操作失败，系统异常，请稍后重试"

    class Page:
        url = "https://www.doubao.com/chat/abc"

        def locator(self, css: str) -> Body | MagicMock:
            if css == "body":
                return Body()
            empty = MagicMock()
            empty.count.return_value = 0
            return empty

        def wait_for_timeout(self, _ms: int) -> None:
            return None

        def get_by_role(self, *_a, **_k) -> MagicMock:
            empty = MagicMock()
            empty.count.return_value = 0
            return empty

    with patch(
        "aperix_geo.services.providers.doubao_web.runtime.assert_logged_in",
        return_value=None,
    ), patch(
        "aperix_geo.services.providers.doubao_web.runtime.assert_no_captcha",
        return_value=None,
    ):
        with pytest.raises(DoubaoCrawlError, match="系统异常") as exc_info:
            _wait_until(
                Page(),
                deadline=999999.0,
                predicate=lambda: False,
                label="test",
            )
    assert exc_info.value.session_alive is True


def test_last_assistant_md_skips_prompt_echo() -> None:
    page = _Page()
    page.md_texts = ["今天天气怎么样", "今天多云。"]
    assert _last_assistant_md_text(page, user_prompt="今天天气怎么样") == "今天多云。"


def test_wait_generation_ignores_user_toolbar_until_assistant_text() -> None:
    page = _Page()
    settings = Settings(doubao_crawl_timeout_s=30)
    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._stop_button_visible",
            side_effect=lambda _p: page.stop,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._any_streaming_true",
            side_effect=lambda _p: page.streaming,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._action_bar_visible",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.runtime.assert_logged_in",
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow.assert_no_captcha",
        ),
    ):
        _wait_generation_done(
            page,
            settings=settings,
            deadline=__import__("time").monotonic() + 5,
            user_prompt="问一句",
        )
    assert page.md_texts == ["助手正文"]
    assert page.waits >= 2


def test_extract_skips_prompt_only_clipboard() -> None:
    page = _Page()
    page.md_texts = ["问一句"]
    with patch(
        "aperix_geo.services.providers.doubao_web.ui_flow._copy_assistant_markdown_via_toolbar",
        return_value="问一句",
    ):
        assert _extract_assistant_text(page, user_prompt="问一句") == ""


def test_extract_search_panel_expands_and_clicks_tabs() -> None:
    page = MagicMock()
    page.url = "https://www.doubao.com/chat/sample12345678"

    hint = MagicMock()
    hint.is_visible.return_value = True
    hint.bounding_box.return_value = {"x": 400, "y": 100, "width": 200, "height": 24}

    tab = MagicMock()
    tab.is_visible.return_value = True
    tab.inner_text.return_value = "参考资料"

    panel_root = MagicMock()
    panel_root.inner_text.return_value = "搜索 2 个关键词\nhttps://example.com/a"
    panel_root.locator.return_value.count.return_value = 0
    panel_root.get_by_role.return_value.count.return_value = 0
    panel_root.get_by_text.return_value = MagicMock(
        count=lambda: 1,
        nth=lambda _i: tab,
    )

    page.get_by_text.return_value = MagicMock(count=lambda: 1, nth=lambda _i: hint)

    first_visible_calls = 0

    def _fake_first_visible(_locator: object, *, limit: int = 12) -> MagicMock:
        nonlocal first_visible_calls
        first_visible_calls += 1
        return hint if first_visible_calls == 1 else tab

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._first_visible",
            side_effect=_fake_first_visible,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._panel_root",
            return_value=panel_root,
        ),
    ):
        text, hrefs = _extract_search_panel(page)

    hint.click.assert_called_once()
    assert tab.click.call_count == 2
    assert "搜索 2 个关键词" in text
    assert hrefs == ()


def test_more_menu_button_scopes_to_chat_header() -> None:
    from aperix_geo.services.providers.doubao_web import selectors as sel
    from aperix_geo.services.providers.doubao_web.ui_flow import _more_menu_button

    trigger = MagicMock()
    trigger.is_visible.return_value = True

    header_loc = MagicMock()
    header_loc.count.return_value = 1
    header_loc.nth.return_value = trigger

    main = MagicMock()
    main.count.return_value = 1

    page = MagicMock()

    def _page_locator(css: str) -> MagicMock:
        if css == sel.CHAT_MAIN:
            return main
        if css == sel.CHAT_HEADER_MORE_TRIGGER:
            return header_loc
        return MagicMock(count=lambda: 0)

    page.locator.side_effect = _page_locator

    found = _more_menu_button(page)

    page.locator.assert_any_call(sel.CHAT_HEADER_MORE_TRIGGER)
    assert found is trigger


def test_share_menuitem_in_menu_picks_share_among_rows() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _share_menuitem_in_menu

    def _item(label: str) -> MagicMock:
        item = MagicMock()
        item.is_visible.return_value = True
        label_loc = MagicMock()
        label_loc.count.return_value = 1
        label_loc.inner_text.return_value = label
        truncate = MagicMock()
        truncate.first = label_loc
        item.locator.return_value = truncate
        return item

    rename = _item("重命名")
    share = _item("分享")

    menu = MagicMock()
    menu.locator.return_value = MagicMock(
        count=lambda: 2,
        nth=lambda i: rename if i == 0 else share,
    )

    assert _share_menuitem_in_menu(menu) is share


def test_locate_share_control_finds_menuitem_in_open_dropdown() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _locate_share_control

    share_row = MagicMock()
    menu = MagicMock()
    page = MagicMock()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._iter_visible_locators",
            return_value=[menu],
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._share_menuitem_in_menu",
            return_value=share_row,
        ),
    ):
        found = _locate_share_control(page)

    assert found is share_row


def test_conversation_share_menu_open_when_menuitem_visible() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _conversation_share_menu_open

    page = MagicMock()
    with patch(
        "aperix_geo.services.providers.doubao_web.ui_flow._header_overflow_menu_ready",
        return_value=True,
    ):
        assert _conversation_share_menu_open(page) is True

    with patch(
        "aperix_geo.services.providers.doubao_web.ui_flow._header_overflow_menu_ready",
        return_value=False,
    ):
        assert _conversation_share_menu_open(page) is False


def test_open_chat_more_menu_clicks_when_header_menu_not_ready() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _open_chat_more_menu

    btn = MagicMock()
    page = MagicMock()
    share_row = MagicMock()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._header_overflow_menu_ready",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._locate_share_control",
            return_value=share_row,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._more_menu_button",
            return_value=btn,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._dismiss_overlay",
        ) as dismiss,
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._activate_header_more_button",
        ) as activate,
    ):
        ok = _open_chat_more_menu(page)

    assert ok is True
    dismiss.assert_called_once()
    activate.assert_called_once_with(page, btn)


def test_open_chat_more_menu_clicks_even_if_share_visible_but_header_closed() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _open_chat_more_menu

    btn = MagicMock()
    page = MagicMock()
    share_row = MagicMock()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._header_overflow_menu_ready",
            return_value=False,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._locate_share_control",
            return_value=share_row,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._more_menu_button",
            return_value=btn,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._dismiss_overlay",
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._activate_header_more_button",
        ) as activate,
    ):
        ok = _open_chat_more_menu(page)

    assert ok is True
    activate.assert_called_once_with(page, btn)


def test_open_chat_more_menu_skips_click_when_menu_already_open() -> None:
    from aperix_geo.services.providers.doubao_web.ui_flow import _open_chat_more_menu

    page = MagicMock()
    share_row = MagicMock()

    with (
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._header_overflow_menu_ready",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._locate_share_control",
            return_value=share_row,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._more_menu_button",
            return_value=MagicMock(),
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._activate_header_more_button",
        ) as activate,
    ):
        ok = _open_chat_more_menu(page)

    assert ok is True
    activate.assert_not_called()
