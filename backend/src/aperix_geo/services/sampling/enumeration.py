"""Extract named spans from list-like patterns in AI response text (enumeration hints)."""

from __future__ import annotations

import re

_ENUM_SEP = re.compile(r"[、,/;；|]")
_PAREN = re.compile(r"[（(]([^）)]+)[）)]")
_TRAILING_ETC = re.compile(r"(?:等|等等|之类|etc\.?|…|\.\.\.)$", re.IGNORECASE)
_SLASH_RUN = re.compile(
    r"(?<![/\w])"
    r"([\u4e00-\u9fff\w][\u4e00-\u9fff\w·\-]{0,24}"
    r"(?:/[\u4e00-\u9fff\w][\u4e00-\u9fff\w·\-]{0,24})+)"
    r"(?![/\w])"
)
_NOISE = re.compile(r"^[\d\s·\-_.]+$")
_URL_SPAN = re.compile(r"https?://\S+", re.IGNORECASE)
_LEADING_JUNK = re.compile(
    r"^(?:如|若|例如|比如|包括|以及|或者|还有|同时吃|如果同时吃|如果|当|在|用|吃|服|选|可(?:选|以)?|有没有)"
)
_QUESTION = re.compile(r"(?:有没有|是否|吗|？|\?)")
_SENTENCE_START = re.compile(r"^(?:如果|若|有没有|是否|可以|需要|准备|不要|不能|出现|长期|随意|告诉|愿意|梳理)")
_VERB_FRAGMENT = re.compile(
    r"(?:如果|同时|自行|随意|准备|不要|不能|出现|长期|告诉|可以帮|愿意|梳理|复查|留意|警惕|优先|需要|应该|可能|会|要|别|有没有)"
)
_SYMPTOM_PHRASE = re.compile(
    r"(?:出血|异常|不适|疼痛|头晕|恶心|腹胀|皮疹|淤斑|黑便|呕血|黄疸|乏力|酸痛|糜烂|胃痛|牙龈|皮肤)$"
)
# 病史 / 风险描述（非可监测商业主体）
_HISTORY_PHRASE = re.compile(r"^.+史$")
_RISK_PHRASE = re.compile(r"^.+(?:风险|倾向|症状|综合征|并发症)$")
_BODY_PART = re.compile(r"^(?:牙龈|皮肤|胃部|肝脏|眼睛|眼白|肌肉|血管|大便|小便|血脂|肝功|肌酶)$")
_CATEGORY_PHRASE = re.compile(
    r"^(?:他汀|他汀类|抗血小板|降压降糖|银杏制剂|活血(?:类|药)|中成药|西药|降糖|降压)$"
)
_ANTI_CATEGORY = re.compile(r"^抗[\u4e00-\u9fff]{1,4}$")
_TREATMENT_PAIR = re.compile(r"^降[\u4e00-\u9fff]{1,3}降[\u4e00-\u9fff]{1,3}$")
_DESCRIPTIVE_CLAUSE = re.compile(
    r"(?:辅助|改善|用于|预防|治疗|降低|升高|包括|评估|监测|复查|联用|叠加|告知|优先|核心|基础|常见|重点|主要|风险|要点|建议|清单|实操)"
)


def _text_without_urls(text: str) -> str:
    return _URL_SPAN.sub(" ", text)

_MIN_LEN = 2
_MAX_LEN = 48


def _normalize_item(raw: str) -> str:
    item = raw.strip().strip("\"'“”‘’")
    item = item.strip("*# ")
    item = _TRAILING_ETC.sub("", item).strip()
    return item


def normalize_mention_span(raw: str) -> str:
    """Strip leading junk and trailing descriptive clauses from a candidate span."""
    item = _normalize_item(str(raw or ""))
    if not item:
        return ""
    item = _LEADING_JUNK.sub("", item).strip()
    if re.search(r"[，,；;：:]", item):
        parts = re.split(r"[，,；;：:]", item, maxsplit=1)
        head = parts[0].strip()
        tail = parts[1].strip() if len(parts) > 1 else ""
        if head and tail and (_looks_descriptive_clause(tail) or len(tail) >= 6):
            item = head
    return item.strip()


def _looks_descriptive_clause(text: str) -> bool:
    return bool(_DESCRIPTIVE_CLAUSE.search(text) or _VERB_FRAGMENT.search(text))


def is_plausible_commercial_span(label: str) -> bool:
    """Reject category words, symptoms, and sentence fragments masquerading as brand names."""
    text = normalize_mention_span(label)
    if len(text) < 3 or len(text) > 32:
        return False
    if _NOISE.match(text):
        return False
    if _URL_SPAN.search(text) or "://" in text or text.startswith("www."):
        return False
    if _QUESTION.search(text):
        return False
    if _SENTENCE_START.search(text):
        return False
    if _VERB_FRAGMENT.search(text) and len(text) > 6:
        return False
    if _CATEGORY_PHRASE.match(text):
        return False
    if _ANTI_CATEGORY.match(text):
        return False
    if _TREATMENT_PAIR.match(text):
        return False
    if _BODY_PART.match(text):
        return False
    if text.endswith("类") and len(text) <= 8:
        return False
    if re.match(r"^[\u4e00-\u9fff]{1,4}药$", text):
        return False
    if _SYMPTOM_PHRASE.search(text) and len(text) <= 10:
        return False
    if _HISTORY_PHRASE.match(text) and len(text) <= 8:
        return False
    if _RISK_PHRASE.match(text) and len(text) <= 12:
        return False
    if re.search(r"(?:出血|过敏|手术|既往)", text) and len(text) <= 8:
        return False
    return True


def _appears_in_text(item: str, text: str) -> bool:
    if not item or not text:
        return False
    if item.isascii():
        return item.lower() in text.lower()
    return item in text


def _is_valid_candidate(item: str, text: str) -> bool:
    normalized = normalize_mention_span(item)
    if len(normalized) < _MIN_LEN or len(normalized) > _MAX_LEN:
        return False
    if not is_plausible_commercial_span(normalized):
        return False
    if _NOISE.match(normalized):
        return False
    if _URL_SPAN.search(normalized) or "://" in normalized or normalized.startswith("www."):
        return False
    if not _appears_in_text(normalized, text):
        return False
    return True


def _split_enum_chunk(chunk: str) -> list[str]:
    parts = _ENUM_SEP.split(chunk)
    items: list[str] = []
    for part in parts:
        item = _normalize_item(part)
        if item:
            items.append(item)
    return items


def _extract_from_parentheses(text: str) -> list[str]:
    items: list[str] = []
    for match in _PAREN.finditer(text):
        inner = match.group(1).strip()
        if not inner or "://" in inner or "www." in inner.lower():
            continue
        if not _ENUM_SEP.search(inner):
            continue
        items.extend(_split_enum_chunk(inner))
    return items


def _extract_slash_runs(text: str) -> list[str]:
    items: list[str] = []
    for match in _SLASH_RUN.finditer(_text_without_urls(text)):
        chunk = match.group(1)
        items.extend(_split_enum_chunk(chunk))
    return items


def extract_enumerated_spans(text: str) -> list[str]:
    """Return deduplicated spans from parenthetical or slash-separated enumerations."""
    if not text.strip():
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    def add_many(raw_items: list[str]) -> None:
        for item in raw_items:
            key = item.casefold() if item.isascii() else item
            if key in seen:
                continue
            if not _is_valid_candidate(item, text):
                continue
            seen.add(key)
            ordered.append(item)

    add_many(_extract_from_parentheses(text))
    add_many(_extract_slash_runs(text))
    return ordered


def filter_mention_spans(spans: list[str], text: str) -> list[str]:
    """Keep spans that literally appear in text; dedupe preserving order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in spans:
        item = normalize_mention_span(str(raw or ""))
        if not item:
            continue
        key = item.casefold() if item.isascii() else item
        if key in seen:
            continue
        if not _is_valid_candidate(item, text):
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def merge_mention_candidates(text: str, *extra_lists: list[str]) -> list[str]:
    """Merge rule-based enumeration spans with optional discovery spans."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add_many(items: list[str]) -> None:
        for item in items:
            normalized = normalize_mention_span(item)
            if not normalized or not is_plausible_commercial_span(normalized):
                continue
            key = normalized.casefold() if normalized.isascii() else normalized
            if key in seen:
                continue
            seen.add(key)
            ordered.append(normalized)

    add_many(extract_enumerated_spans(text))
    for extra in extra_lists:
        if extra:
            add_many(filter_mention_spans(extra, text))
    return ordered
