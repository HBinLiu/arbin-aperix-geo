"""Shared GEO web-crawl service (resident browser for Doubao / DeepSeek / Qianwen / …)."""

from aperix_geo.services.geo_web_crawl.client import run_geo_web_crawl_job
from aperix_geo.services.geo_web_crawl.registry import list_platforms

__all__ = ["run_geo_web_crawl_job", "list_platforms"]
