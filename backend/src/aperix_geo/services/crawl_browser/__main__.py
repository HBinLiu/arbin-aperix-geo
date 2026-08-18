"""Run resident crawl-browser HTTP server.

  PYTHONPATH=src python -m aperix_geo.services.crawl_browser
  # or: uvicorn aperix_geo.services.crawl_browser.server:app --host 0.0.0.0 --port 9410
"""

from __future__ import annotations

import logging
import os


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("GEO_WEB_CRAWL_LOG_LEVEL", "INFO"),
        format="%(levelname)s: %(message)s",
    )
    host = (os.environ.get("GEO_WEB_CRAWL_HOST") or "0.0.0.0").strip() or "0.0.0.0"
    port = int(os.environ.get("GEO_WEB_CRAWL_PORT") or "9410")
    import uvicorn

    uvicorn.run(
        "aperix_geo.services.crawl_browser.server:app",
        host=host,
        port=port,
        log_level=(os.environ.get("GEO_WEB_CRAWL_LOG_LEVEL") or "info").lower(),
        workers=1,  # Sync Playwright pool is process-local; scale with replicas.
    )


if __name__ == "__main__":
    main()
