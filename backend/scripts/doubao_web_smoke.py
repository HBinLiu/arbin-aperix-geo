#!/usr/bin/env python3
"""Local smoke: one Doubao Web crawl with storage_state (does not touch Celery).

Usage (from backend/):

  export PYTHONPATH=src
  export DOUBAO_CRAWL_STORAGE_STATE_PATH=data/doubao_storage_state.json
  export DOUBAO_CRAWL_HEADLESS=false   # optional, easier to debug
  python3 scripts/doubao_web_smoke.py "适合小团队的 CRM 有哪些"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.config import get_settings  # noqa: E402
from aperix_geo.services.providers.doubao_web.crawler import crawl_doubao_chat  # noqa: E402
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError  # noqa: E402


def main() -> int:
    prompt = " ".join(sys.argv[1:]).strip() or "用一两句话介绍一下什么是 GEO 优化"
    settings = get_settings()
    if not (settings.doubao_crawl_storage_state_path or "").strip():
        print(
            "Set DOUBAO_CRAWL_STORAGE_STATE_PATH (run scripts/doubao_web_login.py first)",
            file=sys.stderr,
        )
        return 1

    print(f"Crawling prompt={prompt!r} headless={settings.doubao_crawl_headless}")
    try:
        result = crawl_doubao_chat([{"role": "user", "content": prompt}], settings=settings)
    except DoubaoCrawlError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    payload = {
        "text": result.text[:500],
        "text_len": len(result.text),
        "search_queries": list(result.search_queries),
        "source_urls": list(result.source_urls),
        "share_url": result.share_url,
        "web_search_mode": result.web_search_mode,
        "latency_ms": result.latency_ms,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
