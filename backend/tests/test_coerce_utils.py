"""Tests for coercion helpers."""

from aperix_geo.utils.coerce import pick_str, safe_float, safe_int


def test_safe_int() -> None:
    assert safe_int({"n": "3"}, "n") == 3
    assert safe_int({"n": "x"}, "n", default=7) == 7
    assert safe_int({}, "missing", default=1) == 1


def test_safe_float() -> None:
    assert safe_float({"n": "1.5"}, "n") == 1.5
    assert safe_float({}, "n") is None
    assert safe_float({"n": "bad"}, "n") is None


def test_pick_str() -> None:
    data = {"title": "  Hello ", "empty": "   "}
    assert pick_str(data, "missing", "title") == "Hello"
    assert pick_str(data, "empty", "missing") == ""
