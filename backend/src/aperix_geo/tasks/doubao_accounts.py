"""Celery tasks for Doubao account pool."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="aperix_geo.tasks.doubao_accounts.doubao_account_heartbeat", ignore_result=True)
def doubao_account_heartbeat() -> dict[str, Any]:
    """Periodic login probe for Doubao crawl accounts (no-op when disabled)."""
    db = SessionLocal()
    try:
        from aperix_geo.services.doubao_accounts.heartbeat import run_doubao_account_heartbeat

        result = run_doubao_account_heartbeat(db)
        if not result.get("skipped"):
            logger.info(
                "doubao heartbeat checked=%s ok=%s failed=%s",
                result.get("checked"),
                result.get("ok_count"),
                result.get("failed"),
            )
        return result
    except Exception:
        db.rollback()
        logger.exception("doubao account heartbeat failed")
        raise
    finally:
        db.close()
