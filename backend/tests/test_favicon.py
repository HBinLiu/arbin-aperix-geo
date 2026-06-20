from aperix_geo.services.favicon import normalize_favicon_domain
from aperix_geo.services.favicon._fetch import sniff_image
from aperix_geo.services.favicon._parse import parse_link_icons, parse_meta_images
from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced


def test_normalize_favicon_domain() -> None:
    from aperix_geo.services.favicon._domain import (
        is_favicon_homepage_url,
        normalize_favicon_domain,
        resolve_favicon_request_url,
    )

    assert normalize_favicon_domain("huanqiulvzhou.com") == "huanqiulvzhou.com"
    assert normalize_favicon_domain("example.com") == "example.com"
    assert normalize_favicon_domain("www.Airwallex.com") == "airwallex.com"
    assert normalize_favicon_domain("https://www.shop.foo.com/path") == "shop.foo.com"
    assert normalize_favicon_domain("m.example.com.cn") == "m.example.com.cn"
    assert normalize_favicon_domain("yjj.gxzf.gov.cn") == "yjj.gxzf.gov.cn"
    assert normalize_favicon_domain("m.iefans.net") == "m.iefans.net"
    assert normalize_favicon_domain("https://m.iefans.net/android/1728638.html") == "m.iefans.net"

    resolved = resolve_favicon_request_url("https://geowise.newrank.cn/")
    assert resolved == ("geowise.newrank.cn", "https://geowise.newrank.cn/")
    assert is_favicon_homepage_url("https://example.com/", "example.com") is True
    assert is_favicon_homepage_url("https://m.example.com/article", "example.com") is False


def test_favicon_homepage_urls_apex_before_www(monkeypatch) -> None:
    from aperix_geo.services.favicon._domain import favicon_homepage_urls

    monkeypatch.setattr(
        "aperix_geo.utils.url.host_resolves",
        lambda host: host in {"example.com", "www.example.com"},
    )
    urls = favicon_homepage_urls("example.com")
    assert urls[0] == "https://example.com/"
    assert urls[1] == "https://www.example.com/"


def test_favicon_homepage_urls_subdomain_only_self() -> None:
    from aperix_geo.services.favicon._domain import favicon_homepage_urls

    assert favicon_homepage_urls("shop.foo.com") == ["https://shop.foo.com/"]


def test_parse_iefans_shortcut_icon() -> None:
    html = (
        '<link rel="shortcut icon" '
        'href="//staticfile.iefans.net/iefans/theme1/favicon.ico" type="image/x-icon">'
    )
    urls = parse_link_icons(html, "https://m.iefans.net/android/1728638.html")
    assert urls == ["https://staticfile.iefans.net/iefans/theme1/favicon.ico"]


def test_parse_icon_hrefs_rel_after_href() -> None:
    html = '<html><head><link href="/assets/icon.png" rel="icon" type="image/png"></head></html>'
    urls = parse_link_icons(html, "https://example.com/")
    assert urls == ["https://example.com/assets/icon.png"]


def test_parse_icon_hrefs_apple_touch_first() -> None:
    html = """
    <link rel="icon" href="/favicon.ico">
    <link rel="apple-touch-icon" href="/apple.png">
    """
    urls = parse_link_icons(html, "https://shop.test/")
    assert urls[0] == "https://shop.test/apple.png"


def test_parse_shortcut_icon() -> None:
    html = '<link rel="shortcut icon" href="/s.ico">'
    urls = parse_link_icons(html, "https://a.com/")
    assert urls == ["https://a.com/s.ico"]


def test_parse_icon_unquoted_href() -> None:
    html = "<link rel=icon href=/favicon.ico>"
    urls = parse_link_icons(html, "https://example.com/")
    assert urls == ["https://example.com/favicon.ico"]


def test_parse_icon_octet_stream_type() -> None:
    html = '<link rel="icon" href="/f.ico" type="application/octet-stream">'
    urls = parse_link_icons(html, "https://example.com/")
    assert urls == ["https://example.com/f.ico"]


def test_parse_icon_href_before_rel() -> None:
    html = '<link href="//cdn.example.com/icon.png" rel="icon">'
    urls = parse_link_icons(html, "https://www.example.com/")
    assert urls == ["https://cdn.example.com/icon.png"]


def test_parse_icon_absolute_https_url() -> None:
    html = '<link rel="icon" href="https://cdn.example.com/assets/favicon.png?v=2">'
    urls = parse_link_icons(html, "https://www.example.com/")
    assert urls == ["https://cdn.example.com/assets/favicon.png?v=2"]


def test_parse_icon_absolute_http_url() -> None:
    html = '<link rel="shortcut icon" href="http://static.example.org/f.ico">'
    urls = parse_link_icons(html, "https://example.com/")
    assert urls == ["http://static.example.org/f.ico"]


def test_parse_icon_absolute_url_unquoted() -> None:
    html = "<link rel=icon href=https://cdn.example.com/icon.ico>"
    urls = parse_link_icons(html, "https://example.com/page")
    assert urls == ["https://cdn.example.com/icon.ico"]


def test_parse_meta_og_image() -> None:
    html = '<meta property="og:image" content="https://cdn.example.com/logo.png">'
    urls = parse_meta_images(html, "https://example.com/")
    assert urls == ["https://cdn.example.com/logo.png"]


def test_related_hosts_from_html_static_subdomain() -> None:
    from aperix_geo.services.favicon._parse import favicon_urls_for_hosts, related_hosts_from_html

    html = """
    <link rel="stylesheet" href="https://static.11467.com/www/css/b2b.css">
    <img src="//static.11467.com/www/css/logo.gif">
    """
    hosts = related_hosts_from_html(html, "11467.com")
    assert "static.11467.com" in hosts
    assert "https://static.11467.com/favicon.ico" in favicon_urls_for_hosts(hosts)


def test_sniff_rejects_tiny_payload() -> None:
    assert not sniff_image(b"short")
    assert sniff_image(b"\x89PNG\r\n\x1a\n" + b"x" * 100)


def test_persist_favicon_writes_static_file(tmp_path, monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod

    monkeypatch.setattr("aperix_geo.services.favicon._storage._storage_root", lambda: tmp_path)

    body = b"\x89PNG\r\n\x1a\n" + b"x" * 100
    storage_mod.persist_favicon(
        "example.com",
        url="https://cdn.example.com/a.png",
        body=body,
        media_type="image/png",
    )

    index = storage_mod.load_index("example.com")
    assert index["static"] == "favicon.png"
    assert index["media_type"] == "image/png"
    assert (tmp_path / "example.com" / "favicon.png").read_bytes() == body
    assert storage_mod.read_disk_favicon("example.com") == (body, "image/png")


def test_icon_candidates_from_html() -> None:
    from aperix_geo.services.favicon._parse import icon_candidates_from_html

    html = """
    <link rel="icon" href="/favicon.ico">
    <link rel="stylesheet" href="https://static.example.com/app.css">
    """
    urls = icon_candidates_from_html(html, "https://www.example.com/", "example.com")
    assert urls.index("https://www.example.com/favicon.ico") < urls.index(
        "https://static.example.com/favicon.ico",
    )


def test_page_icon_candidates_before_subdomain() -> None:
    from aperix_geo.services.favicon._parse import (
        page_icon_candidates_from_html,
        subdomain_favicon_candidates_from_html,
    )

    html = """
    <meta property="og:image" content="https://cdn.example.com/logo.png">
    <a href="https://mseller.example.com/login">seller</a>
    """
    page = page_icon_candidates_from_html(html, "https://www.example.com/")
    sub = subdomain_favicon_candidates_from_html(html, "example.com")
    assert page == ["https://cdn.example.com/logo.png"]
    assert sub[0] == "https://mseller.example.com/favicon.ico"
    assert "https://mseller.example.com/favicon.png" in sub


def test_subdomain_candidates_skip_www_and_apex() -> None:
    from aperix_geo.services.favicon._parse import subdomain_favicon_candidates_from_html

    html = """
    <img src="https://www.example.com/a.png">
    <img src="https://static.example.com/b.png">
    """
    urls = subdomain_favicon_candidates_from_html(html, "example.com")
    assert "https://www.example.com/favicon.ico" not in urls
    assert "https://example.com/favicon.ico" not in urls
    assert "https://static.example.com/favicon.ico" in urls


def test_discover_icon_url_batches_with_page_url(monkeypatch) -> None:
    from aperix_geo.services.favicon._candidates import discover_icon_url_batches

    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates.icons_from_page_url",
        lambda page_url, timeout_s: ["https://staticfile.example.com/icon.ico"],
    )
    class _FakeSources:
        def page_icons_from_fetch(self) -> list[str]:
            return []

        def page_icons_from_crawl4ai(self) -> list[str]:
            return []

        def subdomain_icons_from_fetch(self) -> list[str]:
            return []

        def subdomain_icons_from_crawl4ai(self) -> list[str]:
            return []

    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates._HomepageHtmlSources",
        lambda domain, timeout_s: _FakeSources(),
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates.main_standard_path_urls",
        lambda _d: [],
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates.cdn_prefix_standard_path_urls",
        lambda _d: [],
    )

    batches = discover_icon_url_batches(
        "m.example.com",
        timeout_s=5.0,
        page_url="https://m.example.com/article",
    )
    assert batches[0] == ["https://staticfile.example.com/icon.ico"]


def test_resolve_favicon_network_with_page_url(monkeypatch) -> None:
    from aperix_geo.services.favicon._fetch import resolve_favicon_network

    calls: list[str | None] = []

    def fake_batches(domain, *, timeout_s, page_url=None):
        calls.append(page_url)
        return [["https://staticfile.example.com/icon.ico"]]

    monkeypatch.setattr(
        "aperix_geo.services.favicon._fetch.discover_icon_url_batches",
        fake_batches,
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._fetch._warm_homepage_cookies",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._fetch.fetch_first_icon",
        lambda client, host, candidates, timeout_s: (b"icon", "image/x-icon"),
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._fetch.get_icon_httpx_client",
        lambda: object(),
    )

    result = resolve_favicon_network(
        "m.iefans.net",
        timeout_s=5.0,
        page_url="https://m.iefans.net/android/1728638.html",
    )
    assert result == (b"icon", "image/x-icon")
    assert calls == ["https://m.iefans.net/android/1728638.html"]


def test_discover_icon_url_batches_order(monkeypatch) -> None:
    from aperix_geo.services.favicon._candidates import discover_icon_url_batches

    class FakeSources:
        def page_icons_from_fetch(self):
            return ["https://www.example.com/icon-from-fetch.png"]

        def page_icons_from_crawl4ai(self):
            return ["https://cdn.example.com/icon-from-crawl.png"]

        def subdomain_icons_from_fetch(self):
            return ["https://mseller.example.com/favicon.ico"]

        def subdomain_icons_from_crawl4ai(self):
            return ["https://api.example.com/favicon.ico"]

    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates._HomepageHtmlSources",
        lambda domain, *, timeout_s: FakeSources(),
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates.main_standard_path_urls",
        lambda _d: ["https://www.example.com/favicon.ico"],
    )
    monkeypatch.setattr(
        "aperix_geo.services.favicon._candidates.cdn_prefix_standard_path_urls",
        lambda _d: ["https://static.example.com/favicon.ico"],
    )

    batches = discover_icon_url_batches("example.com", timeout_s=5.0)
    assert batches[0] == ["https://www.example.com/icon-from-fetch.png"]
    assert batches[1] == ["https://cdn.example.com/icon-from-crawl.png"]
    assert batches[2] == ["https://www.example.com/favicon.ico"]
    assert batches[3] == ["https://mseller.example.com/favicon.ico"]
    assert batches[4] == ["https://api.example.com/favicon.ico"]
    assert batches[5] == ["https://static.example.com/favicon.ico"]


def test_homepage_sources_fetch_page_icons(monkeypatch) -> None:
    from aperix_geo.services.crawl.types import PageFetchResult
    from aperix_geo.services.favicon._candidates import _HomepageHtmlSources

    def fake_fetch_page(url: str, *, crawl, max_chars: int) -> PageFetchResult:
        assert crawl.crawl_fallback is False
        return PageFetchResult(
            url=url,
            final_url=url,
            html='<link rel="icon" href="/from-page.png">',
            source="httpx",
        )

    monkeypatch.setattr("aperix_geo.services.crawl.fetch_page", fake_fetch_page)

    src = _HomepageHtmlSources("example.com", timeout_s=8.0)
    icons = src.page_icons_from_fetch()
    assert any(u.endswith("/from-page.png") for u in icons)
    assert icons[0].endswith("/from-page.png")


def test_homepage_sources_crawl4ai_page_icons(monkeypatch) -> None:
    from aperix_geo.services.favicon._candidates import _HomepageHtmlSources

    def fake_crawl4ai(url: str, *, timeout_s: float, max_chars: int, max_concurrent: int):
        return (
            url,
            '<link rel="icon" href="https://cdn.example.com/rendered.png">',
            "",
            "crawl4ai",
        )

    monkeypatch.setattr(
        "aperix_geo.services.crawl._crawl4ai.fetch_url_crawl4ai",
        fake_crawl4ai,
    )

    src = _HomepageHtmlSources("example.com", timeout_s=8.0)
    icons = src.page_icons_from_crawl4ai()
    assert icons[0] == "https://cdn.example.com/rendered.png"


def test_homepage_sources_crawl4ai_skipped_when_disabled(monkeypatch) -> None:
    from dataclasses import replace

    from aperix_geo.services.crawl.settings import page_crawl_settings
    from aperix_geo.services.favicon._candidates import _HomepageHtmlSources

    called = {"n": 0}

    def fake_crawl4ai(*args, **kwargs):
        called["n"] += 1
        return ("", "", "", "none")

    monkeypatch.setattr(
        "aperix_geo.services.crawl._crawl4ai.fetch_url_crawl4ai",
        fake_crawl4ai,
    )
    monkeypatch.setattr(
        "aperix_geo.services.crawl.settings.page_crawl_settings",
        lambda: replace(page_crawl_settings(), crawl_fallback=False),
    )

    src = _HomepageHtmlSources("example.com", timeout_s=8.0)
    icons = src.page_icons_from_crawl4ai()
    assert icons == []
    assert called["n"] == 0


def test_negative_cache_skips_network(monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod

    storage_mod._cache.clear()
    storage_mod._negative_cache.clear()
    called = {"n": 0}

    def fake_network(*args, **kwargs):
        called["n"] += 1
        return None

    monkeypatch.setattr(
        "aperix_geo.services.favicon._resolve.resolve_favicon_network",
        fake_network,
    )
    storage_mod.negative_cache_set("example.com")

    assert resolve_favicon_coalesced("example.com") is None
    assert called["n"] == 0


def test_negative_cache_set_on_miss(monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod

    storage_mod._cache.clear()
    storage_mod._negative_cache.clear()
    monkeypatch.setattr(
        "aperix_geo.services.favicon._resolve.resolve_favicon_network",
        lambda *args, **kwargs: None,
    )

    assert resolve_favicon_coalesced("miss.example.com") is None
    assert storage_mod.negative_cache_hit("miss.example.com")


def test_coalesced_resolve_hits_memory_cache_on_repeat(monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod

    storage_mod._cache.clear()
    storage_mod._negative_cache.clear()
    calls = {"n": 0}

    def fake_network(host: str, *, timeout_s: float, page_url: str | None = None):
        calls["n"] += 1
        return b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png"

    monkeypatch.setattr(
        "aperix_geo.services.favicon._resolve.resolve_favicon_network",
        fake_network,
    )

    first = resolve_favicon_coalesced("cached.example.com")
    second = resolve_favicon_coalesced("cached.example.com")

    assert first is not None
    assert second == first
    assert calls["n"] == 1


def test_static_favicon_path(tmp_path, monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod

    monkeypatch.setattr("aperix_geo.services.favicon._storage._storage_root", lambda: tmp_path)

    body = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    storage_mod.persist_favicon(
        "disk.example.com",
        url="https://disk.example.com/favicon.png",
        body=body,
        media_type="image/png",
    )

    hit = storage_mod.static_favicon_path("disk.example.com")
    assert hit is not None
    path, media_type = hit
    assert path.is_file()
    assert media_type == "image/png"
    assert path.read_bytes() == body
    assert storage_mod.read_disk_favicon("disk.example.com") == (body, "image/png")


def test_favicon_api_serves_disk_file(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from aperix_geo.main import app
    from aperix_geo.services.favicon import _storage as storage_mod

    monkeypatch.setattr("aperix_geo.services.favicon._storage._storage_root", lambda: tmp_path)

    body = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    storage_mod.persist_favicon(
        "static-api.example.com",
        url="https://static-api.example.com/favicon.png",
        body=body,
        media_type="image/png",
    )

    client = TestClient(app)
    ok = client.get("/api/v1/favicon?url=https://static-api.example.com/")
    assert ok.status_code == 200
    assert ok.content == body
    assert ok.headers["content-type"].startswith("image/png")

    miss = client.get("/api/v1/favicon?url=https://unknown.example.com/")
    assert miss.status_code == 204


def test_warm_favicon_hosts_skips_cached(tmp_path, monkeypatch) -> None:
    from aperix_geo.services.favicon import _storage as storage_mod
    from aperix_geo.services.favicon._warm import warm_favicon_hosts

    monkeypatch.setattr("aperix_geo.services.favicon._storage._storage_root", lambda: tmp_path)
    storage_mod._cache.clear()
    storage_mod._negative_cache.clear()
    called = {"n": 0}

    body = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    storage_mod.persist_favicon(
        "cached-warm.example.com",
        url="https://cached-warm.example.com/favicon.png",
        body=body,
        media_type="image/png",
    )

    def fake_coalesce(host: str, *, timeout_s: float = 5.0):
        called["n"] += 1
        return body, "image/png"

    monkeypatch.setattr(
        "aperix_geo.services.favicon._warm.resolve_favicon_coalesced",
        fake_coalesce,
    )

    stats = warm_favicon_hosts(["cached-warm.example.com", "new.example.com"])
    assert stats["total"] == 2
    assert stats["skipped"] == 1
    assert stats["resolved"] == 1
    assert called["n"] == 1


def test_warm_favicon_hosts_parallel(tmp_path, monkeypatch) -> None:
    import threading
    import time

    from aperix_geo.services.favicon import _storage as storage_mod
    from aperix_geo.services.favicon._warm import warm_favicon_hosts

    monkeypatch.setattr("aperix_geo.services.favicon._storage._storage_root", lambda: tmp_path)
    storage_mod._cache.clear()
    storage_mod._negative_cache.clear()
    active = {"n": 0}
    peak = {"n": 0}
    lock = threading.Lock()
    body = b"\x89PNG\r\n\x1a\n" + b"x" * 20

    def fake_coalesce(host: str, *, timeout_s: float = 5.0):
        with lock:
            active["n"] += 1
            peak["n"] = max(peak["n"], active["n"])
        time.sleep(0.05)
        with lock:
            active["n"] -= 1
        return body, "image/png"

    monkeypatch.setattr(
        "aperix_geo.services.favicon._warm.resolve_favicon_coalesced",
        fake_coalesce,
    )

    hosts = [f"host-{index}.example.com" for index in range(4)]
    stats = warm_favicon_hosts(hosts, concurrency=3, job_id="job-1")
    assert stats == {"total": 4, "skipped": 0, "resolved": 4, "miss": 0}
    assert peak["n"] >= 2
