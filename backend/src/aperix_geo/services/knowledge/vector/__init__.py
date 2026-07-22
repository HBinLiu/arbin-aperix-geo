"""Knowledge vector indexing: chunk, embed, pgvector index."""

from aperix_geo.services.knowledge.vector.chunk import TextChunk, chunk_text, estimate_token_count
from aperix_geo.services.knowledge.vector.embed import embed_texts
from aperix_geo.services.knowledge.vector.index import IndexSubjectResult, index_subject_knowledge

__all__ = [
    "IndexSubjectResult",
    "TextChunk",
    "chunk_text",
    "embed_texts",
    "estimate_token_count",
    "index_subject_knowledge",
]
