"""Tests for embedding client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.knowledge.vector.embed import embed_texts
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError


def test_embed_texts_requires_api_key() -> None:
    settings = Settings(embedding_api_key="", qianwen_api_key="")
    with pytest.raises(KnowledgeIndexError, match="not configured"):
        embed_texts(["hello"], settings=settings)


@patch("aperix_geo.services.knowledge.vector.embed.OpenAI")
def test_embed_texts_returns_vectors(mock_openai_cls: MagicMock) -> None:
    client = MagicMock()
    mock_openai_cls.return_value = client
    item = MagicMock()
    item.embedding = [0.1] * 1024
    client.embeddings.create.return_value = MagicMock(data=[item], usage=None)

    settings = Settings(embedding_api_key="sk-test", embedding_dimensions=1024)
    vectors, usage = embed_texts(["你好"], settings=settings)

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
    assert "latency_ms" in usage
    client.embeddings.create.assert_called_once()
