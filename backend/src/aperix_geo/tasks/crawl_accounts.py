"""Celery tasks for the multi-platform crawl account pool."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO

logger = logging.getLogger(__name__)


@celery_app.task(
    name="aperix_geo.tasks.crawl_accounts.crawl_account_heartbeat",
    ignore_result=True,
)
def crawl_account_heartbeat(platform: str = PLATFORM_DOUBAO) -> dict[str, Any]:
    """Periodic login probe for crawl accounts (no-op when heartbeat disabled)."""
    db = SessionLocal()
    try:
        from aperix_geo.services.crawl_accounts.heartbeat import run_crawl_account_heartbeat

        result = run_crawl_account_heartbeat(db, platform=platform)
        if result.get("skipped"):
            logger.info(
                "crawl heartbeat skipped reason=%s platform=%s",
                result.get("reason"),
                platform,
            )
        else:
            logger.info(
                "crawl heartbeat platform=%s checked=%s ok=%s failed=%s",
                result.get("platform"),
                result.get("checked"),
                result.get("ok_count"),
                result.get("failed"),
            )
        return result
    except Exception:
        db.rollback()
        logger.exception("crawl account heartbeat failed")
        raise
    finally:
        db.close()
