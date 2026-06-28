"""Celery tasks: subscription billing maintenance."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.billing.rollover import process_billing_maintenance

logger = logging.getLogger(__name__)


@celery_app.task(name="aperix_geo.tasks.billing.billing_maintenance")
def billing_maintenance() -> dict[str, Any]:
    """Daily: expire subscriptions and roll AI usage periods."""
    db = SessionLocal()
    try:
        result = process_billing_maintenance(db)
        logger.info(
            "billing maintenance: expired=%d rolled=%d",
            result["expired_subscriptions"],
            result["rolled_usage_periods"],
        )
        return {"ok": True, **result}
    except Exception:
        db.rollback()
        logger.exception("billing maintenance failed")
        raise
    finally:
        db.close()
