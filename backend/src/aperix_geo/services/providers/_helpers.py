"""Shared helpers for sampling providers."""

from __future__ import annotations

import re
from typing import Any

# Models sometimes pack multiple search intents into one tool-call query.
_SEARCH_QUERY_SPLIT_RE = re.compile(
    r"[;；|｜\n\r,，、]+"  # semicolon / pipe / newline / comma /顿号
    r"|(?:\s+/\s+)"  # spaced slash only (avoid ChatGPT/Perplexity)
)


def expand_search_queries(queries: list[str] | tuple[str, ...]) -> list[str]:
    """Split packed provider queries on common delimiters; trim empties."""
    out: list[str] = []
    for raw in queries:
        text = (raw or "").replace("\u3000", " ").strip()
        if not text:
            continue
        for part in _SEARCH_QUERY_SPLIT_RE.split(text):
            query = part.strip()
            if query:
                out.append(query)
    return out


def dedupe_urls(urls: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        url = (raw or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return tuple(out)


def dedupe_search_queries(queries: list[str]) -> tuple[str, ...]:
    """Expand semicolon-joined queries, then preserve first-seen order (no lowercase)."""
    seen: set[str] = set()
    out: list[str] = []
    for query in expand_search_queries(queries):
        if query in seen:
            continue
        seen.add(query)
        out.append(query)
    return tuple(out)


def query_from_tool_args(args: dict[str, Any] | Any) -> str:
    """Pull search query text from provider tool-call argument objects."""
    if not isinstance(args, dict):
        return ""
    for key in ("query", "q", "search_query"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def with_system_prompt(
    messages: list[dict[str, str]],
    system_text: str,
) -> list[dict[str, str]]:
    if messages and messages[0].get("role") == "system":
        return messages
    return [{"role": "system", "content": system_text}, *messages]


def response_data(response: Any, *, extra_attrs: tuple[str, ...] = ()) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    data: dict[str, Any] = {}
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        data = dump(exclude_none=True)
    extra = getattr(response, "model_extra", None)
    if isinstance(extra, dict):
        data = {**data, **extra}
    for attr in extra_attrs:
        if hasattr(response, attr):
            value = getattr(response, attr, None)
            if value is not None:
                data[attr] = value
    return data


def to_plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if hasattr(value, "keys"):
        return {k: to_plain(value[k]) for k in value.keys()}
    return value


def extract_completion_text(response: Any, data: dict[str, Any]) -> str:
    try:
        choices = response.choices  # type: ignore[attr-defined]
        return str(choices[0].message.content or "").strip()
    except (AttributeError, IndexError, TypeError):
        for choice in data.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message") or {}
            if isinstance(message, dict) and message.get("content"):
                return str(message["content"]).strip()
    return ""


def collect_url_field(items: list[Any], *, url_keys: tuple[str, ...] = ("url", "Url")) -> list[str]:
    urls: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            item = to_plain(item)
        if not isinstance(item, dict):
            continue
        for key in url_keys:
            if item.get(key):
                urls.append(str(item[key]))
                break
    return urls
