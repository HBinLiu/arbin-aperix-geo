"""Map Doubao Web samantha SSE / JSON chunks → sampling fields (not OpenAI schema)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from aperix_geo.services.providers._helpers import dedupe_urls
from aperix_geo.services.providers.result import SamplingChatResult

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)


def _loads_maybe(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _iter_sse_data_payloads(raw: str) -> list[Any]:
    payloads: list[Any] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line or line == "[DONE]":
            continue
        try:
            payloads.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not payloads and (raw or "").strip().startswith("{"):
        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return payloads


def _collect_meta(obj: Any, *, queries: list[str], urls: list[str], conv: list[str]) -> None:
    """Collect conversation_id / search queries / cite URLs without assistant text deltas."""
    if isinstance(obj, dict):
        for key in ("conversation_id", "conversationId"):
            val = obj.get(key)
            if val is not None and str(val).strip() not in ("", "0"):
                conv.append(str(val).strip())

        for key in ("search_queries", "queries", "keywords", "search_words"):
            val = obj.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.strip():
                        queries.append(item.strip())
                    elif isinstance(item, dict):
                        q = item.get("query") or item.get("text") or item.get("keyword")
                        if isinstance(q, str) and q.strip():
                            queries.append(q.strip())

        for key in ("search_query", "query", "keyword"):
            q = obj.get(key)
            if isinstance(q, str) and q.strip() and key != "query":
                # bare "query" is too ambiguous; prefer explicit search_* keys above
                queries.append(q.strip())
            elif key.startswith("search_") and isinstance(q, str) and q.strip():
                queries.append(q.strip())

        for key in ("references", "citations", "sources", "search_references"):
            val = obj.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.startswith("http"):
                        urls.append(item)
                    elif isinstance(item, dict):
                        u = item.get("url") or item.get("link") or item.get("source_url")
                        if isinstance(u, str) and u.startswith("http"):
                            urls.append(u)

        for value in obj.values():
            if isinstance(value, (dict, list)):
                _collect_meta(value, queries=queries, urls=urls, conv=conv)
    elif isinstance(obj, list):
        for item in obj:
            _collect_meta(item, queries=queries, urls=urls, conv=conv)


def _extract_message_text(event_data: Any) -> str:
    if not isinstance(event_data, dict):
        return ""
    message = event_data.get("message")
    if not isinstance(message, dict):
        return ""
    content = _loads_maybe(message.get("content"))
    if isinstance(content, dict):
        text = content.get("text")
        return text if isinstance(text, str) else ""
    return ""


def map_sse_events_to_fields(raw: str) -> dict[str, Any]:
    """Parse samantha SSE body into text / search_queries / source_urls / conversation_id."""
    texts: list[str] = []
    queries: list[str] = []
    urls: list[str] = []
    conv: list[str] = []

    for payload in _iter_sse_data_payloads(raw):
        if not isinstance(payload, dict):
            continue

        if "event_type" in payload:
            event_data = _loads_maybe(payload.get("event_data"))
            event_type = payload.get("event_type")
            if event_type == 2002 and isinstance(event_data, dict):
                cid = event_data.get("conversation_id")
                if cid is not None and str(cid).strip() not in ("", "0"):
                    conv.append(str(cid).strip())
            if event_type == 2001:
                delta = _extract_message_text(event_data)
                if delta:
                    texts.append(delta)
            _collect_meta(event_data, queries=queries, urls=urls, conv=conv)
            continue

        # Non-SSE JSON fallback
        delta = _extract_message_text(payload)
        if delta:
            texts.append(delta)
        elif isinstance(payload.get("text"), str) and payload["text"]:
            texts.append(payload["text"])
        _collect_meta(payload, queries=queries, urls=urls, conv=conv)

    joined = "".join(texts)
    for match in _URL_RE.findall(joined):
        urls.append(match.rstrip(").,;]}'\""))

    clean_urls: list[str] = []
    for u in dedupe_urls(urls):
        try:
            host = (urlparse(u).hostname or "").lower()
        except Exception:
            continue
        if host.endswith("doubao.com") or host.endswith("byteimg.com"):
            continue
        clean_urls.append(u)

    seen_q: set[str] = set()
    clean_queries: list[str] = []
    for q in queries:
        if q not in seen_q:
            seen_q.add(q)
            clean_queries.append(q)

    return {
        "text": joined.strip(),
        "search_queries": clean_queries,
        "source_urls": clean_urls,
        "conversation_id": conv[-1] if conv else "",
    }


def map_web_http_to_sampling_result(
    fields: dict[str, Any],
    *,
    latency_ms: int,
    share_url: str = "",
) -> SamplingChatResult:
    """Direct map to SamplingChatResult (no OpenAI message/SSE façade)."""
    return SamplingChatResult(
        text=str(fields.get("text") or "").strip(),
        usage={},
        latency_ms=int(latency_ms),
        source_urls=tuple(fields.get("source_urls") or ()),
        web_search_mode="doubao_web_crawl",
        search_queries=tuple(fields.get("search_queries") or ()),
        share_url=(share_url or "").strip(),
    )
