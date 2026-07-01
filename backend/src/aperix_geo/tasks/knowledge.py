"""Knowledge indexing Celery tasks."""

from __future__ import annotations

import logging
from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError, KnowledgeNotReadyError
from aperix_geo.services.knowledge.index import index_subject_knowledge

logger = logging.getLogger(__name__)


@celery_app.task(
    name="aperix_geo.tasks.knowledge.index_subject",
    bind=True,
    max_retries=3,
    autoretry_for=(KnowledgeIndexError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def index_subject(self, subject_id: str) -> dict[str, object]:
    """Embed and persist knowledge chunks for a verified subject."""
    sid = UUID(subject_id)
    db = SessionLocal()
    try:
        result = index_subject_knowledge(db, sid)
        db.commit()
        return {
            "subject_id": str(result.subject_id),
            "knowledge_version": result.knowledge_version,
            "chunks_created": result.chunks_created,
            "chunks_skipped": result.chunks_skipped,
            "sources_indexed": result.sources_indexed,
        }
    except KnowledgeNotReadyError:
        db.rollback()
        logger.warning("knowledge index skipped: subject_id=%s not ready", subject_id)
        raise
    except Exception:
        db.commit()
        raise
    finally:
        db.close()
