"""Knowledge indexing errors."""


class KnowledgeIndexError(Exception):
    """Base error for knowledge index pipeline."""


class KnowledgeNotReadyError(KnowledgeIndexError):
    """Subject knowledge missing or not verified for indexing."""
