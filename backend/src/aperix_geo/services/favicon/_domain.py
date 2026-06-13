"""Domain normalization and homepage URL selection."""

from __future__ import annotations

from aperix_geo.utils.domains import registrable_domain, strip_hostname
from aperix_geo.utils.url import homepage_urls_apex_first


def normalize_favicon_domain(raw: str) -> str:
    """
    归一 favicon 主机名：去 www / 端口；gov 等子站保留完整主机名（如 yjj.gxzf.gov.cn）。

    主域（wise.com）仍归一为 eTLD+1；多一级子域不折叠到父域，避免抓错 favicon。
    """
    host = strip_hostname(raw).split(":")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    root = registrable_domain(host)
    if root and host != root and host.endswith(f".{root}"):
        return host
    return root or host


def favicon_homepage_urls(host: str) -> list[str]:
    """favicon 抓取用的首页候选。

    - 子域（gov 子站、shop.foo.com）只请求自身主机。
    - 裸域（example.com，无 www 前缀）优先 apex，再试 www。
    """
    host = host.strip().lower()
    if not host:
        return []
    root = registrable_domain(host)
    if root and host != root and host.endswith(f".{root}"):
        return [f"https://{host}/"]

    return homepage_urls_apex_first(root or host) or [f"https://{host}/"]
