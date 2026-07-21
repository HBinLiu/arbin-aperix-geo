"""Tests for URL type helpers (rs-trafilatura optional)."""

from __future__ import annotations

from types import ModuleType
from unittest.mock import MagicMock, patch

from aperix_geo.services.url_type import classify_url, normalize_url_type
from aperix_geo.services.url_type.extract import _coerce_page_type, extract_main_content


def test_normalize_url_type() -> None:
    assert normalize_url_type("Documentation") == "documentation"
    assert normalize_url_type("docs") == "documentation"
    assert normalize_url_type("category") == "collection"
    assert normalize_url_type("nope") == "other"
    assert normalize_url_type("") == "other"


def test_coerce_page_type() -> None:
    assert _coerce_page_type(("documentation", 0.9)) == "documentation"
    assert _coerce_page_type("PageType.Forum") == "forum"
    assert _coerce_page_type(None) == "other"


def test_classify_url_empty() -> None:
    assert classify_url("") == "other"


def test_classify_url_without_package_is_other() -> None:
    real_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "rs_trafilatura":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        assert classify_url("https://docs.example.com/guide") == "other"


def test_classify_url_uses_official_package() -> None:
    mock_mod = ModuleType("rs_trafilatura")
    mock_mod.classify_url = MagicMock(return_value=("documentation", 0.9))  # type: ignore[attr-defined]
    real_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "rs_trafilatura":
            return mock_mod
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        assert classify_url("https://docs.example.com/api") == "documentation"
        mock_mod.classify_url.assert_called_once_with("https://docs.example.com/api")  # type: ignore[attr-defined]


def test_extract_main_content_without_package() -> None:
    real_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "rs_trafilatura":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        body, page_type = extract_main_content("<html><body><p>hello</p></body></html>")
        assert body == ""
        assert page_type == ""


def test_extract_main_content_uses_package() -> None:
    mock_result = MagicMock()
    mock_result.text = "Clean article body " * 5
    mock_result.page_type = "article"
    mock_mod = ModuleType("rs_trafilatura")
    mock_mod.extract = MagicMock(return_value=mock_result)  # type: ignore[attr-defined]
    real_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "rs_trafilatura":
            return mock_mod
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        body, page_type = extract_main_content(
            "<html><body><p>noise</p></body></html>",
            url="https://example.com/a",
        )
        assert body.startswith("Clean article body")
        assert page_type == "article"
