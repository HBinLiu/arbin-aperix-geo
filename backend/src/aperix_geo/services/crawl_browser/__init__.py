"""Resident Playwright browser for Doubao / DeepSeek / Qianwen crawl jobs."""

from aperix_geo.services.crawl_browser.client import run_crawl_job
from aperix_geo.services.crawl_browser.registry import list_platforms

__all__ = ["run_crawl_job", "list_platforms"]
