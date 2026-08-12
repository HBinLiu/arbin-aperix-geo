"""Tests for SEO / GEO metadata extraction."""

from aperix_geo.services.crawl.seo import (
    SeoProfile,
    apply_seo_profile,
    parse_seo_from_html,
    seo_has_signal,
    seo_prose_text,
)


def test_parse_seo_twitter_and_keywords() -> None:
    html = """
    <head>
    <meta name="keywords" content="GEO, AI 可见性, 品牌监测" />
    <meta name="twitter:title" content="Twitter 标题" />
    <meta name="twitter:description" content="Twitter 描述" />
    </head>
    """
    seo = parse_seo_from_html(html)
    assert seo.title == "Twitter 标题"
    assert seo.description == "Twitter 描述"
    assert "GEO" in seo.keywords
    assert seo_has_signal(seo)


def test_parse_seo_json_ld_item_list() -> None:
    html = """
    <html><head><title>榜单</title></head><body>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "ItemList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "item": {"@type": "Product", "name": "Profound"}},
        {"@type": "ListItem", "position": 2, "item": {"@type": "Product", "name": "Otterly"}}
      ]
    }
    </script>
    </body></html>
    """
    seo = parse_seo_from_html(html)
    assert seo.title == "榜单"
    assert "Profound" in seo.mentioned_names
    assert "Otterly" in seo.mentioned_names
    assert "ItemList" in seo.schema_types


def test_parse_seo_article_mentions() -> None:
    html = """
    <head>
    <meta property="article:tag" content="GEO 工具" />
    <meta property="article:tag" content="AI 搜索" />
    </head>
    <script type="application/ld+json">
    {
      "@type": "Article",
      "headline": "2025 GEO 工具对比",
      "description": "对比 Profound 与 Otterly 等主流平台",
      "mentions": [{"@type": "Organization", "name": "Profound"}]
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.title == "2025 GEO 工具对比"
    assert "Profound" in seo.mentioned_names
    assert "GEO 工具" in seo.tags
    prose = seo_prose_text(seo)
    assert "mentions:" in prose
    assert "tags:" in prose


def test_parse_seo_canonical_and_og_type() -> None:
    html = """
    <head>
    <link rel="canonical" href="https://example.com/geo-tools" />
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="Digitaling" />
    <meta property="article:section" content="营销科技" />
    <meta property="article:author" content="张三" />
    </head>
    """
    seo = parse_seo_from_html(html)
    assert seo.canonical_url == "https://example.com/geo-tools"
    assert seo.content_type == "article"
    assert seo.site_name == "Digitaling"
    assert "营销科技" in seo.categories
    assert "张三" in seo.authors


def test_parse_seo_site_name_application_name_fallback() -> None:
    html = """
    <head>
    <meta name="application-name" content="万里汇" />
    <title>跨境支付指南</title>
    </head>
    """
    seo = parse_seo_from_html(html)
    assert seo.site_name == "万里汇"


def test_parse_seo_site_name_from_json_ld_website() -> None:
    html = """
    <head><title>Some Article</title></head>
    <script type="application/ld+json">
    {
      "@type": "WebSite",
      "name": "36氪",
      "url": "https://36kr.com/"
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.site_name == "36氪"


def test_parse_seo_site_name_from_publisher() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "NewsArticle",
      "headline": "市场观察",
      "publisher": {"@type": "Organization", "name": "第一财经"}
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.publisher == "第一财经"
    assert seo.site_name == "第一财经"


def test_parse_seo_site_name_from_is_part_of_website() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "Article",
      "headline": "深度报道",
      "isPartOf": {"@type": "WebSite", "name": "财新"}
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.site_name == "财新"


def test_parse_seo_site_name_from_title_with_base_url() -> None:
    html = """
    <head><title>万里汇 | 跨境支付平台</title></head>
    """
    seo = parse_seo_from_html(html, base_url="https://www.wise.com/zh-cn/")
    assert seo.site_name == "万里汇"


def test_usable_site_name_rejects_long_strings() -> None:
    from aperix_geo.services.crawl.seo import MAX_SITE_NAME_LEN, usable_site_name

    assert usable_site_name("万里汇") == "万里汇"
    assert usable_site_name("Aperix AI") == "Aperix AI"
    assert usable_site_name("x" * (MAX_SITE_NAME_LEN + 1)) == ""
    from aperix_geo.services.crawl.seo import coalesce_site_name

    assert coalesce_site_name(site_name="首页", publisher="Acme") == "Acme"
    assert coalesce_site_name(title="wise.com", domain="wise.com") == ""
    assert coalesce_site_name(breadcrumbs=["Home", "Products", "Pay"]) == "Products"


def test_coalesce_site_name_rejects_page_title_as_site_name() -> None:
    from aperix_geo.services.crawl.seo import coalesce_site_name

    title = "如何做好跨境支付选型指南"
    assert (
        coalesce_site_name(
            site_name=title,
            publisher="万里汇",
            title=title,
            domain="wise.com",
        )
        == "万里汇"
    )
    assert (
        coalesce_site_name(
            site_name=title,
            title=f"{title} | 万里汇",
            domain="wise.com",
        )
        == "万里汇"
    )


def test_parse_seo_rejects_og_site_name_equal_to_title() -> None:
    html = """
    <head>
    <title>深度报道：市场观察</title>
    <meta property="og:site_name" content="深度报道：市场观察" />
    <meta property="og:type" content="article" />
    </head>
    <script type="application/ld+json">
    {
      "@type": "NewsArticle",
      "headline": "深度报道：市场观察",
      "publisher": {"@type": "Organization", "name": "第一财经"}
    }
    </script>
    """
    seo = parse_seo_from_html(html, base_url="https://www.yicai.com/news/1.html")
    assert seo.site_name == "第一财经"


def test_parse_seo_faq_page() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "FAQPage",
      "mainEntity": [{
        "@type": "Question",
        "name": "什么是 GEO？",
        "acceptedAnswer": {"@type": "Answer", "text": "GEO 是生成式引擎优化。"}
      }, {
        "@type": "Question",
        "name": "Profound 是什么？",
        "acceptedAnswer": {"@type": "Answer", "text": "Profound 是 AI 可见性监测平台。"}
      }]
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert len(seo.faq_items) == 2
    assert any("Profound" in item for item in seo.faq_items)
    assert "Profound" in seo.mentioned_names or any("Profound" in item for item in seo.faq_items)
    prose = seo_prose_text(seo)
    assert "faq:" in prose


def test_parse_seo_software_application() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "SoftwareApplication",
      "name": "SheepGeo",
      "applicationCategory": "BusinessApplication",
      "brand": {"@type": "Brand", "name": "SheepGeo"}
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert "SheepGeo" in seo.mentioned_names
    assert "SheepGeo" in seo.brand_names
    assert "BusinessApplication" in seo.categories


def test_parse_seo_breadcrumbs() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://example.com/"},
        {"@type": "ListItem", "position": 2, "name": "GEO 工具", "item": "https://example.com/geo"}
      ]
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.breadcrumbs == ("首页", "GEO 工具")


def test_parse_seo_microdata_fallback() -> None:
    html = """
    <div itemscope itemtype="https://schema.org/Product">
      <span itemprop="name">Otterly</span>
      <span itemprop="brand">Otterly Inc</span>
      <meta itemprop="description" content="AI search monitoring platform" />
    </div>
    """
    seo = parse_seo_from_html(html)
    assert "Otterly" in seo.mentioned_names
    assert "Otterly Inc" in seo.brand_names
    assert seo.description == "AI search monitoring platform"


def test_parse_seo_speakable_text() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "WebPage",
      "name": "GEO Guide",
      "speakable": {
        "@type": "SpeakableSpecification",
        "text": "Profound and Otterly are leading GEO analytics platforms."
      }
    }
    </script>
    """
    seo = parse_seo_from_html(html)
    assert seo.speakable_text
    assert "Profound" in seo.speakable_text[0]


def test_seo_prose_empty() -> None:
    assert seo_prose_text(parse_seo_from_html("")) == ""


def test_apply_seo_profile_site_head_strips_article_fields() -> None:
    html = """
    <head>
    <title>Profound</title>
    <meta name="description" content="GEO platform" />
    <meta property="article:tag" content="GEO" />
    </head>
    <script type="application/ld+json">
    {
      "@type": "FAQPage",
      "mainEntity": [{"@type": "Question", "name": "Q?", "acceptedAnswer": {"@type": "Answer", "text": "A"}}]
    }
    </script>
    """
    full = parse_seo_from_html(html)
    scoped = apply_seo_profile(full, SeoProfile.SITE_HEAD)
    assert scoped.title == "Profound"
    assert scoped.description == "GEO platform"
    assert scoped.tags == ()
    assert scoped.faq_items == ()
    prose = seo_prose_text(full, profile=SeoProfile.SITE_HEAD)
    assert "tags:" not in prose
    assert "faq:" not in prose


def test_apply_seo_profile_subject_homepage_keeps_product_signals() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "SoftwareApplication",
      "name": "SheepGeo",
      "applicationCategory": "BusinessApplication",
      "brand": {"name": "SheepGeo"}
    }
    </script>
    """
    full = parse_seo_from_html(html)
    subject = apply_seo_profile(full, SeoProfile.SUBJECT_HOMEPAGE)
    assert "SheepGeo" in subject.brand_names
    assert "BusinessApplication" in subject.categories


def test_apply_seo_profile_site_head() -> None:
    html = """
    <script type="application/ld+json">
    {"@type": "SoftwareApplication", "name": "Profound", "brand": {"name": "Profound"}}
    </script>
    """
    full = parse_seo_from_html(html)
    scoped = apply_seo_profile(full, SeoProfile.SITE_HEAD)
    assert "Profound" in scoped.brand_names
    assert "SoftwareApplication" in scoped.schema_types
    assert scoped.tags == ()


def test_parse_seo_skips_microdata_when_disabled() -> None:
    html = """
    <head><title>Head Only</title></head>
    <body itemscope itemtype="https://schema.org/Product">
      <span itemprop="name">Microdata Brand</span>
    </body>
    """
    with_micro = parse_seo_from_html(html, include_microdata=True)
    without_micro = parse_seo_from_html(html, include_microdata=False)
    assert "Microdata Brand" in with_micro.mentioned_names or "Microdata Brand" in with_micro.brand_names
    assert without_micro.title == "Head Only"
    assert "Microdata Brand" not in without_micro.mentioned_names
    assert "Microdata Brand" not in without_micro.brand_names


def test_parse_seo_cache_reuses_result() -> None:
    from aperix_geo.services.crawl.seo import clear_seo_parse_cache

    clear_seo_parse_cache()
    html = "<head><title>Cached Title</title></head>"
    first = parse_seo_from_html(html, include_microdata=False)
    second = parse_seo_from_html(html, include_microdata=False)
    assert first.title == second.title == "Cached Title"
    assert first is second
