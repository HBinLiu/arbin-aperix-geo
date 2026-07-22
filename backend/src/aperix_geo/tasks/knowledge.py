"""Knowledge indexing / graph-extract Celery tasks."""

from __future__ import annotations

import logging
from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.knowledge.exceptions import (
    KnowledgeExtractError,
    KnowledgeIndexError,
    KnowledgeNotReadyError,
)
from aperix_geo.services.knowledge.graph.extract import extract_subject_knowledge
from aperix_geo.services.knowledge.vector.index import index_subject_knowledge

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
        if result.superseded:
            from aperix_geo.services.knowledge.persist import enqueue_knowledge_index

            enqueue_knowledge_index(sid)
        return {
            "subject_id": str(result.subject_id),
            "knowledge_version": result.knowledge_version,
            "chunks_created": result.chunks_created,
            "chunks_skipped": result.chunks_skipped,
            "sources_indexed": result.sources_indexed,
            "superseded": result.superseded,
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


@celery_app.task(
    name="aperix_geo.tasks.knowledge.extract_subject",
    bind=True,
    max_retries=2,
    autoretry_for=(KnowledgeExtractError,),
    retry_backoff=True,
    retry_backoff_max=180,
    retry_jitter=True,
)
def extract_subject(self, subject_id: str) -> dict[str, object]:
    """Extract entity/relation graph into subject knowledge relations_json."""
    sid = UUID(subject_id)
    db = SessionLocal()
    try:
        result = extract_subject_knowledge(db, sid)
        db.commit()
        return {
            "subject_id": str(result.subject_id),
            "knowledge_version": result.knowledge_version,
            "node_count": result.node_count,
            "edge_count": result.edge_count,
            "extract_status": result.extract_status,
        }
    except KnowledgeNotReadyError:
        db.rollback()
        logger.warning("knowledge extract skipped: subject_id=%s not ready", subject_id)
        raise
    except Exception:
        db.commit()
        raise
    finally:
        db.close()
