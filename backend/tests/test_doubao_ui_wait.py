"""Wait-for-reply must not treat the user-message toolbar as generation end."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.ui_flow import (
    _extract_assistant_text,
    _extract_search_panel,
    _last_assistant_md_text,
    _require_sample_conversation,
    _wait_generation_done,
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


def test_require_sample_conversation_reopens_drifted_thread() -> None:
    page = MagicMock()
    page.url = "https://www.doubao.com/chat/other-thread"

    def _goto(_url: str, **_kwargs: object) -> None:
        page.url = "https://www.doubao.com/chat/sample12345678"

    page.goto.side_effect = _goto
    _require_sample_conversation(
        page,
        conversation_id="sample12345678",
        base_url="https://www.doubao.com/chat/",
    )
    page.goto.assert_called_once_with(
        "https://www.doubao.com/chat/sample12345678",
        wait_until="domcontentloaded",
        timeout=15_000,
    )


def test_extract_search_panel_expands_and_clicks_tabs() -> None:
    page = MagicMock()
    page.url = "https://www.doubao.com/chat/sample12345678"

    hint = MagicMock()
    hint.is_visible.return_value = True
    hint.bounding_box.return_value = {"x": 400, "y": 100, "width": 200, "height": 24}

    tab = MagicMock()
    tab.is_visible.return_value = True

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
            "aperix_geo.services.providers.doubao_web.ui_flow._pin_sample_thread",
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._first_visible",
            side_effect=_fake_first_visible,
        ),
        patch(
            "aperix_geo.services.providers.doubao_web.ui_flow._panel_root",
            return_value=panel_root,
        ),
    ):
        text, hrefs = _extract_search_panel(
            page,
            conversation_id="sample12345678",
            base_url="https://www.doubao.com/chat/",
        )

    hint.click.assert_called_once()
    assert tab.click.call_count >= 1
    assert "搜索 2 个关键词" in text
    assert hrefs == ()
