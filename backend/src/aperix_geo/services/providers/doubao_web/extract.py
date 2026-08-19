"""Extraction helpers for Doubao Web (panel text + md-box HTML → Markdown).

Reply body preferred path (crawler): message toolbar「复制」→ clipboard Markdown.
``md-box-root`` HTML→Markdown remains the DOM fallback. Fan-out / citations stay
in the separate search panel.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from aperix_geo.services.providers._helpers import dedupe_search_queries, dedupe_urls
from aperix_geo.services.providers.doubao_web.selectors import (
    CAPTCHA_TEXT,
    QUOTED_QUERY,
    SEARCH_PANEL_FULL,
    SEARCH_PANEL_HINT,
    SEARCH_PANEL_TAIL,
    SHARE_PATH,
    UI_CHROME_LINE,
)
from aperix_geo.utils.url import extract_urls as _extract_urls_from_text

# Doubao thread id in /chat/<id> (blank landing is /chat/ with no id segment).
_CHAT_CONVERSATION_ID = re.compile(r"/chat/([0-9a-zA-Z_-]{8,})(?:/|$)", re.IGNORECASE)

_BLOCK_TAGS = frozenset(
    {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul", "ol", "li", "table", "pre", "hr"}
)


def conversation_id_from_url(url: str) -> str:
    """Return Doubao conversation id from URL, or '' for blank /chat/ landing."""
    path = urlparse(url or "").path or ""
    match = _CHAT_CONVERSATION_ID.search(path)
    return match.group(1) if match else ""


def conversation_url(base_url: str, conversation_id: str) -> str:
    """Build ``/chat/<id>`` URL for reopening a sample thread."""
    root = (base_url or "").strip().rstrip("/") or "https://www.doubao.com/chat"
    cid = (conversation_id or "").strip()
    if not cid or cid == "0":
        return root + "/"
    if root.endswith("/chat"):
        return f"{root}/{cid}"
    return f"{root.rstrip('/')}/{cid}"


def blank_chat_failure_reason(
    *,
    url: str,
    md_box_texts: list[str],
    message_like_count: int,
    search_panel_hint: bool,
    prior_conversation_id: str = "",
) -> str:
    """Return why the page is not a blank new chat, or '' if OK to send prompt.

    Hard rules (any one fails):
    - still on the same conversation id as before opening a new chat
    - assistant ``.md-box-root`` already has body text
    - prior-turn search panel chrome is visible
    - too many message-like nodes (likely history bubbles)
    """
    current_id = conversation_id_from_url(url)
    prior = (prior_conversation_id or "").strip()
    if prior and current_id and current_id == prior:
        return f"still on prior conversation id={current_id}"

    nonempty_boxes = [t.strip() for t in md_box_texts if (t or "").strip()]
    if nonempty_boxes:
        preview = nonempty_boxes[0][:80].replace("\n", " ")
        return f"assistant md-box history present (n={len(nonempty_boxes)}, preview={preview!r})"

    if search_panel_hint:
        return "search panel from prior turn visible"

    # Welcome chrome may add 1–2 nodes; history threads are denser.
    if message_like_count > 2:
        return f"message-like nodes={message_like_count}"

    return ""


def page_looks_like_captcha(text: str) -> bool:
    """True when visible page text matches Doubao behavior-captcha copy."""
    return bool(CAPTCHA_TEXT.search(text or ""))


def extract_quoted_queries(panel_text: str) -> tuple[str, ...]:
    """Pull search keywords wrapped in quotes from the search panel body."""
    if not (panel_text or "").strip():
        return ()
    found = [m.group(1).strip() for m in QUOTED_QUERY.finditer(panel_text) if m.group(1).strip()]
    return dedupe_search_queries(found)


def extract_urls(text: str) -> tuple[str, ...]:
    if not (text or "").strip():
        return ()
    return dedupe_urls([_strip_url_trailing(u) for u in _extract_urls_from_text(text)])


def is_http_url(url: str) -> bool:
    raw = (url or "").strip()
    if not raw.startswith("http"):
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    return bool(parsed.hostname)


def filter_http_urls(urls: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return dedupe_urls([u for u in urls if is_http_url(u)])


def md_box_html_to_markdown(html: str) -> str:
    """Convert Doubao ``md-box-root`` HTML into Markdown for ``raw_text`` storage."""
    if not (html or "").strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".md-box-root") or soup.select_one("[data-streaming]") or soup
    # Drop table chrome (copy/download icons) while keeping the real <table>.
    for junk in root.select("svg, .action-btn-NhM0gh, [class*='action-btn'], [class*='actions-']"):
        junk.decompose()
    for wrapper in root.select("[data-visual-line-ignore]"):
        table = wrapper.find("table")
        if table is not None:
            wrapper.replace_with(table)
        else:
            wrapper.decompose()
    md = _element_to_markdown(root).strip()
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def clean_assistant_text(
    text: str,
    *,
    user_prompt: str = "",
    search_queries: tuple[str, ...] | list[str] = (),
) -> str:
    """Light cleanup for fallback plain-text paths (md-box Markdown usually needs none)."""
    if not (text or "").strip():
        return ""
    # Already looks like structured Markdown from md-box — keep as-is aside from chrome lines.
    if re.search(r"(?m)^#{1,6}\s+\S", text) or re.search(r"(?m)^[-*]\s+\S", text) or "|" in text:
        lines = []
        prompt = (user_prompt or "").strip()
        for ln in text.splitlines():
            s = ln.strip()
            if UI_CHROME_LINE.match(s):
                continue
            if prompt and s == prompt:
                continue
            if SEARCH_PANEL_HINT.search(s):
                continue
            lines.append(ln)
        return "\n".join(lines).strip()

    # Legacy polluted plain text (pre-md-box extraction).
    return _clean_legacy_plain_text(text, user_prompt=user_prompt, search_queries=search_queries)


def panel_present(text: str) -> bool:
    return bool(SEARCH_PANEL_HINT.search(text or ""))


def panel_counts(text: str) -> tuple[int, int] | None:
    match = SEARCH_PANEL_FULL.search(text or "")
    if not match:
        return None
    return int(match.group("nq")), int(match.group("nr"))


def pick_share_url(candidates: list[str] | tuple[str, ...]) -> str:
    cleaned = [u.strip() for u in candidates if is_http_url(u)]
    if not cleaned:
        return ""
    for url in cleaned:
        if SHARE_PATH.search(urlparse(url).path or ""):
            return url
    return cleaned[0]


def _element_to_markdown(node: Tag | NavigableString | None, *, list_depth: int = 0) -> str:
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        text = str(node)
        if not text or not text.strip():
            return " " if text else ""
        return re.sub(r"\s+", " ", text)

    if not isinstance(node, Tag):
        return ""

    name = (node.name or "").lower()
    if name in {"script", "style", "svg"}:
        return ""

    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        body = _inline_children(node).strip()
        return f"\n\n{'#' * level} {body}\n\n" if body else ""

    if name == "blockquote":
        inner = _block_children(node, list_depth=list_depth).strip()
        if not inner:
            return ""
        quoted = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in inner.splitlines())
        return f"\n\n{quoted}\n\n"

    if name in {"ul", "ol"}:
        items: list[str] = []
        index = 1
        for child in node.children:
            if not isinstance(child, Tag) or (child.name or "").lower() != "li":
                continue
            item_body = _block_children(child, list_depth=list_depth + 1).strip()
            prefix = f"{index}. " if name == "ol" else "- "
            index += 1
            indent = "  " * list_depth
            lines = item_body.splitlines() or [""]
            chunk = f"{indent}{prefix}{lines[0]}"
            for cont in lines[1:]:
                chunk += f"\n{indent}  {cont}"
            items.append(chunk)
        return ("\n" + "\n".join(items) + "\n") if items else ""

    if name == "li":
        return _block_children(node, list_depth=list_depth)

    if name == "table":
        return _table_to_markdown(node)

    if name == "hr":
        return "\n\n---\n\n"

    if name == "br":
        return "\n"

    if name in {"strong", "b"}:
        body = _inline_children(node).strip()
        return f"**{body}**" if body else ""

    if name in {"em", "i"}:
        body = _inline_children(node).strip()
        return f"*{body}*" if body else ""

    if name == "code" and (node.parent is None or (node.parent.name or "").lower() != "pre"):
        return f"`{_inline_children(node).strip()}`"

    if name == "pre":
        return f"\n\n```\n{node.get_text()}\n```\n\n"

    if name == "a":
        label = _inline_children(node).strip() or (node.get("href") or "").strip()
        href = (node.get("href") or "").strip()
        if href.startswith("http") and label:
            return f"[{label}]({href})"
        return label

    if name in {"p"} or (
        name == "div"
        and not node.find(_BLOCK_TAGS - {"div"}, recursive=False)
        and not node.find(["ul", "ol", "table", "h1", "h2", "h3", "blockquote"], recursive=False)
    ):
        body = _inline_children(node).strip()
        return f"\n\n{body}\n\n" if body else ""

    # Generic container: walk children as blocks.
    return _block_children(node, list_depth=list_depth)


def _block_children(node: Tag, *, list_depth: int = 0) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
            continue
        if isinstance(child, Tag):
            parts.append(_element_to_markdown(child, list_depth=list_depth))
    return "".join(parts)


def _inline_children(node: Tag) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(re.sub(r"\s+", " ", str(child)))
            continue
        if isinstance(child, Tag):
            name = (child.name or "").lower()
            if name in _BLOCK_TAGS:
                # Unexpected block inside inline context — flatten.
                parts.append(_element_to_markdown(child).strip())
            else:
                parts.append(_element_to_markdown(child))
    return "".join(parts)


def _table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        rows.append([re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in cells])
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [r + [""] * (width - len(r)) for r in rows]
    header = norm[0]
    body = norm[1:] if len(norm) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n\n" + "\n".join(lines) + "\n\n"


def _clean_legacy_plain_text(
    text: str,
    *,
    user_prompt: str = "",
    search_queries: tuple[str, ...] | list[str] = (),
) -> str:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    prompt = (user_prompt or "").strip()
    query_set = {q.strip() for q in search_queries if (q or "").strip()}
    filtered: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            if filtered and filtered[-1] != "":
                filtered.append("")
            continue
        if UI_CHROME_LINE.match(s):
            continue
        if prompt and s == prompt:
            continue
        if SEARCH_PANEL_HINT.search(s):
            continue
        if _is_query_dump_line(s, query_set):
            continue
        if s in query_set:
            continue
        filtered.append(ln)
    while filtered:
        head = filtered[0].strip()
        if not head:
            filtered.pop(0)
            continue
        if len(head) <= 40 and "。" not in head and "，" not in head[:20] and "：" not in head:
            filtered.pop(0)
            break
        break
    body = "\n".join(filtered).strip()
    if SEARCH_PANEL_HINT.search(body):
        parts = SEARCH_PANEL_HINT.split(body, maxsplit=1)
        after = SEARCH_PANEL_TAIL.sub("", parts[1].strip() if len(parts) > 1 else "").strip()
        before = parts[0].strip()
        body = after if len(after) >= len(before) else (after or before)
    return body.strip()


def _is_query_dump_line(line: str, query_set: set[str]) -> bool:
    quotes = [m.group(1).strip() for m in QUOTED_QUERY.finditer(line)]
    if len(quotes) >= 2:
        return True
    if len(quotes) == 1 and len(line.strip()) <= len(quotes[0]) + 6:
        return True
    if query_set and quotes and all(q in query_set for q in quotes):
        return True
    if "”、“" in line or '","' in line or "」、「" in line:
        return True
    return False


def _strip_url_trailing(url: str) -> str:
    return url.rstrip(".,;:!?，。；：、")
