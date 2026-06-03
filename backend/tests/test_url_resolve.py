"""Tests for resolve_website_url."""

from unittest.mock import MagicMock, patch

import httpx

from aperix_geo.utils.url import fallback_website_url, resolve_website_url, root_website_url


def test_root_website_url() -> None:
    assert root_website_url("https://www.Example.com/path?q=1") == "https://www.example.com"


def test_resolve_website_url_without_probe() -> None:
    domain, url = resolve_website_url("https://www.stripe.com/pricing", probe=False)
    assert domain == "stripe.com"
    assert url == fallback_website_url("stripe.com")


@patch("aperix_geo.utils.url.host_resolves", return_value=False)
def test_resolve_website_url_probe_success(_mock_resolve: MagicMock) -> None:
    class _Client:
        def get(self, url: str, **kwargs):  # noqa: ANN003
            if url == "https://example.com":
                return httpx.Response(200, request=httpx.Request("GET", url))
            raise httpx.HTTPError("unreachable")

        def __enter__(self):
            return self

        def __exit__(self, *args):  # noqa: ANN002
            return False

    with patch("aperix_geo.utils.url.httpx.Client", return_value=_Client()):
        domain, url = resolve_website_url("example.com", probe=True, timeout_s=1.0)

    assert domain == "example.com"
    assert url == "https://example.com"
