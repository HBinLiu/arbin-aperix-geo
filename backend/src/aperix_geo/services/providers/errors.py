"""Provider exception hierarchy."""

from __future__ import annotations


class ProviderError(Exception):
    """Base for sampling provider failures."""


class LLMProviderError(ProviderError):
    """Internal DeepSeek chat_completion failures."""


class SearxngProviderError(ProviderError):
    pass


class DoubaoProviderError(ProviderError):
    pass


class QianwenProviderError(ProviderError):
    pass


class YuanbaoProviderError(ProviderError):
    pass


class ErnieProviderError(ProviderError):
    pass


class DeepseekProviderError(SearxngProviderError):
    pass


class KimiProviderError(SearxngProviderError):
    pass
