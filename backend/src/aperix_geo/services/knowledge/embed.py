"""Embedding API client (OpenAI-compatible /embeddings)."""

from __future__ import annotations

import logging
import time
from typing import Any

from openai import APIError, APITimeoutError, OpenAI

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError

logger = logging.getLogger(__name__)


def _effective_embedding_api_key(settings: Settings) -> str:
    key = settings.embedding_api_key.strip()
    if key:
        return key
    return settings.qianwen_api_key.strip()


def embed_texts(
    texts: list[str],
    *,
    settings: Settings | None = None,
) -> tuple[list[list[float]], dict[str, Any]]:
    """
    Embed a batch of texts. Returns (vectors, usage_dict).
    Raises KnowledgeIndexError on API failure.
    """
    if not texts:
        return [], {}

    cfg = settings or get_settings()
    api_key = _effective_embedding_api_key(cfg)
    if not api_key:
        raise KnowledgeIndexError("EMBEDDING_API_KEY (or QIANWEN_API_KEY) is not configured")

    client = OpenAI(
        base_url=cfg.embedding_base_url.rstrip("/"),
        api_key=api_key,
        max_retries=0,
        timeout=cfg.embedding_timeout_s,
    )
    started = time.perf_counter()
    try:
        response = client.embeddings.create(
            model=cfg.embedding_model,
            input=texts,
            dimensions=cfg.embedding_dimensions,
        )
    except APITimeoutError as exc:
        raise KnowledgeIndexError("embedding API timeout") from exc
    except APIError as exc:
        raise KnowledgeIndexError(f"embedding API error: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    vectors = [list(item.embedding) for item in response.data]
    if len(vectors) != len(texts):
        raise KnowledgeIndexError(
            f"embedding count mismatch: expected {len(texts)}, got {len(vectors)}"
        )

    expected_dim = cfg.embedding_dimensions
    for idx, vec in enumerate(vectors):
        if len(vec) != expected_dim:
            raise KnowledgeIndexError(
                f"embedding dimension mismatch at index {idx}: expected {expected_dim}, got {len(vec)}"
            )

    usage: dict[str, Any] = {}
    if response.usage is not None:
        dump = getattr(response.usage, "model_dump", None)
        usage = dump(exclude_none=True) if callable(dump) else dict(response.usage)
    usage["latency_ms"] = latency_ms
    logger.debug(
        "embedded batch size=%s model=%s latency_ms=%s",
        len(texts),
        cfg.embedding_model,
        latency_ms,
    )
    return vectors, usage
