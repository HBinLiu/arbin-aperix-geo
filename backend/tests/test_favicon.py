from aperix_geo.services.favicon import (
    _parse_icon_hrefs,
    _parse_link_icons,
    _parse_meta_images,
    _sniff_image,
    normalize_favicon_domain,
)


def test_normalize_favicon_domain() -> None:
    assert normalize_favicon_domain("huanqiulvzhou.com") == "huanqiulvzhou.com"
    assert normalize_favicon_domain("www.Airwallex.com") == "airwallex.com"
    assert normalize_favicon_domain("https://www.shop.foo.com/path") == "foo.com"
    assert normalize_favicon_domain("m.example.com.cn") == "example.com.cn"


def test_parse_icon_hrefs_rel_after_href() -> None:
    html = '<html><head><link href="/assets/icon.png" rel="icon" type="image/png"></head></html>'
    urls = _parse_icon_hrefs(html, "https://example.com/")
    assert urls == ["https://example.com/assets/icon.png"]


def test_parse_icon_hrefs_apple_touch_first() -> None:
    html = """
    <link rel="icon" href="/favicon.ico">
    <link rel="apple-touch-icon" href="/apple.png">
    """
    urls = _parse_icon_hrefs(html, "https://shop.test/")
    assert urls[0] == "https://shop.test/apple.png"


def test_parse_shortcut_icon() -> None:
    html = '<link rel="shortcut icon" href="/s.ico">'
    urls = _parse_link_icons(html, "https://a.com/")
    assert urls == ["https://a.com/s.ico"]


def test_parse_icon_unquoted_href() -> None:
    html = "<link rel=icon href=/favicon.ico>"
    urls = _parse_link_icons(html, "https://example.com/")
    assert urls == ["https://example.com/favicon.ico"]


def test_parse_icon_octet_stream_type() -> None:
    html = '<link rel="icon" href="/f.ico" type="application/octet-stream">'
    urls = _parse_link_icons(html, "https://example.com/")
    assert urls == ["https://example.com/f.ico"]


def test_parse_icon_href_before_rel() -> None:
    html = '<link href="//cdn.example.com/icon.png" rel="icon">'
    urls = _parse_link_icons(html, "https://www.example.com/")
    assert urls == ["https://cdn.example.com/icon.png"]


def test_parse_icon_absolute_https_url() -> None:
    html = '<link rel="icon" href="https://cdn.example.com/assets/favicon.png?v=2">'
    urls = _parse_link_icons(html, "https://www.example.com/")
    assert urls == ["https://cdn.example.com/assets/favicon.png?v=2"]


def test_parse_icon_absolute_http_url() -> None:
    html = '<link rel="shortcut icon" href="http://static.example.org/f.ico">'
    urls = _parse_link_icons(html, "https://example.com/")
    assert urls == ["http://static.example.org/f.ico"]


def test_parse_icon_absolute_url_unquoted() -> None:
    html = "<link rel=icon href=https://cdn.example.com/icon.ico>"
    urls = _parse_link_icons(html, "https://example.com/page")
    assert urls == ["https://cdn.example.com/icon.ico"]


def test_parse_meta_og_image() -> None:
    html = '<meta property="og:image" content="https://cdn.example.com/logo.png">'
    urls = _parse_meta_images(html, "https://example.com/")
    assert urls == ["https://cdn.example.com/logo.png"]


def test_sniff_rejects_tiny_payload() -> None:
    assert not _sniff_image(b"short")
    assert _sniff_image(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
