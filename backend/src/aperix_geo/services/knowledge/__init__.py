"""Brand knowledge base: chunking, embedding, indexing."""

from aperix_geo.services.knowledge.chunk import TextChunk, chunk_text
from aperix_geo.services.knowledge.embed import embed_texts
from aperix_geo.services.knowledge.index import IndexSubjectResult, index_subject_knowledge
from aperix_geo.services.knowledge.exceptions import KnowledgeIndexError, KnowledgeNotReadyError

__all__ = [
    "IndexSubjectResult",
    "KnowledgeIndexError",
    "KnowledgeNotReadyError",
    "TextChunk",
    "chunk_text",
    "embed_texts",
    "index_subject_knowledge",
]
