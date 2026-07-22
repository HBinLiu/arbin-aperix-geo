"""Knowledge indexing / extract errors."""


class KnowledgeIndexError(Exception):
    """Base error for knowledge index pipeline."""


class KnowledgeNotReadyError(KnowledgeIndexError):
    """Subject knowledge missing or not verified for indexing."""


class KnowledgeExtractError(Exception):
    """Base error for knowledge graph extract pipeline."""
