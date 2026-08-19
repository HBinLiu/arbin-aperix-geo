"""Apply response ABSA onto entity signal drafts (mentions + sentiment)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject
from aperix_geo.services.brand.domain import extract_domain_from_text_for_brand, other_entity_id
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.services.sampling.mentions import (
    CompetitorEntry,
    absa_brand_mentioned,
    count_term,
    first_idx_any,
    host_mentions_domain,
)
from aperix_geo.utils.sentiment import clamp_sentiment_score
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, compute_mention_ranks


def absa_sentiment_source(response_absa: dict[str, Any]) -> str:
    if not response_absa:
        return "none"
    if response_absa.get("analysis_source") == "failed":
        return "failed"
    if response_absa.get("analysis_source") == "llm" and isinstance(
        response_absa.get("brands_sentiment_absa"), dict
    ):
        return "llm"
    return "failed"


def absa_brand_sentiment(entry: Any) -> tuple[float | None, str | None]:
    if not isinstance(entry, dict) or entry.get("mentioned") is False:
        return None, None
    score_raw = entry.get("score")
    try:
        absa_score = float(score_raw) if score_raw is not None else None
    except (TypeError, ValueError):
        absa_score = None
    if absa_score is None:
        return None, None
    points = clamp_sentiment_score(absa_score)
    reason = str(entry.get("evidence") or "").strip() or None
    return points, reason


def reset_sentiment_drafts(drafts: list[EntitySignalDraft]) -> None:
    for draft in drafts:
        draft.sentiment_score = None
        draft.sentiment_reason = None


def degrade_absa_failure(drafts: list[EntitySignalDraft]) -> None:
    """ABSA unavailable: keep text-based mentions; clear LLM sentiment only."""
    reset_sentiment_drafts(drafts)
    compute_mention_ranks(drafts)


def _rank_hint_from_absa(text: str, brand_key: str, entry: Any) -> int | None:
    idx = first_idx_any(text, (brand_key,))
    if idx is not None:
        return idx
    if not text or not isinstance(entry, dict):
        return None
    evidence = str(entry.get("evidence") or "").strip()
    if not evidence:
        return None
    pos = text.casefold().find(evidence.casefold())
    return pos if pos >= 0 else None


def _fallback_rank_hint(text: str) -> int:
    return len(text) if text else 0


def _evidence_snippet(text: str, label: str, *, max_len: int = 120) -> str:
    if not text or not label:
        return ""
    lowered = text.casefold()
    needle = label.casefold()
    idx = lowered.find(needle)
    if idx < 0:
        return label
    start = max(0, idx - 40)
    end = min(len(text), idx + len(label) + 40)
    snippet = text[start:end].strip()
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1] + "…"
    return snippet


def _is_open_candidate_label(label: str) -> bool:
    text = label.strip()
    if len(text) < 2:
        return False
    if text.endswith("类") and len(text) <= 8:
        return False
    return True


def _absa_explicitly_denied(label: str, response_absa: dict[str, Any]) -> bool:
    others = response_absa.get("other_brands_sentiment_absa")
    if not isinstance(others, dict):
        return False
    entry = others.get(label)
    return isinstance(entry, dict) and entry.get("mentioned") is False


def _other_brand_has_domain_link(label: str, text: str, url_hosts: list[str]) -> bool:
    if not url_hosts:
        return False
    domain = extract_domain_from_text_for_brand(text, label, None)
    return bool(domain and host_mentions_domain(domain, url_hosts))


def _competitor_keys_by_label(
    competitor_absa_keys: list[tuple[str, str]],
) -> dict[str, list[str]]:
    keys_by_label: dict[str, list[str]] = {}
    for absa_key, output_label in competitor_absa_keys:
        keys_by_label.setdefault(output_label, []).append(absa_key)
    return keys_by_label


def _apply_absa_mentions(
    drafts: list[EntitySignalDraft],
    brands: dict[str, Any],
    *,
    own_brand: str,
    own_absa_keys: list[tuple[str, str]],
    competitor_absa_keys: list[tuple[str, str]],
    url_hosts: list[str] | None,
    competitors: list[CompetitorEntry] | None,
    text: str,
) -> None:
    by_entity_label = {draft.entity_label: draft for draft in drafts}
    own_draft = next(draft for draft in drafts if draft.entity_kind == "own")
    own_keys = _competitor_keys_by_label(own_absa_keys).get(own_draft.entity_label, [own_brand])
    own_flags = [absa_brand_mentioned(brands, key) for key in own_keys]
    own_resolved = [flag for flag in own_flags if flag is not None]
    if own_resolved:
        if any(own_resolved):
            own_draft.mentioned = True
            if own_draft.mention_count == 0:
                own_draft.mention_count = 1
            if own_draft.rank_hint_first_index is None:
                for key in own_keys:
                    hint = _rank_hint_from_absa(text, key, brands.get(key))
                    if hint is not None:
                        own_draft.rank_hint_first_index = hint
                        break
                if own_draft.rank_hint_first_index is None:
                    own_draft.rank_hint_first_index = _fallback_rank_hint(text)
        else:
            own_draft.mentioned = False
            own_draft.mention_count = 0
            own_draft.rank_hint_first_index = None

    entries_by_label = {entry.label: entry for entry in (competitors or [])}
    for output_label, keys in _competitor_keys_by_label(competitor_absa_keys).items():
        draft = by_entity_label.get(output_label)
        if draft is None:
            continue
        flags = [absa_brand_mentioned(brands, key) for key in keys]
        resolved = [flag for flag in flags if flag is not None]
        if not resolved:
            continue
        if any(resolved):
            draft.mentioned = True
            if draft.mention_count == 0:
                draft.mention_count = 1
            if draft.rank_hint_first_index is None:
                for key in keys:
                    hint = _rank_hint_from_absa(text, key, brands.get(key))
                    if hint is not None:
                        draft.rank_hint_first_index = hint
                        break
                if draft.rank_hint_first_index is None:
                    draft.rank_hint_first_index = _fallback_rank_hint(text)
        else:
            entry = entries_by_label.get(output_label)
            host_only = (
                draft.mentioned
                and draft.mention_count == 0
                and entry is not None
                and host_mentions_domain(entry.domain, url_hosts or [])
            )
            if host_only:
                continue
            draft.mentioned = False
            draft.mention_count = 0
            draft.rank_hint_first_index = None


def _absa_entry_for_competitor(
    brands: dict[str, Any],
    keys: list[str],
) -> Any:
    for key in keys:
        entry = brands.get(key)
        if isinstance(entry, dict) and entry.get("mentioned"):
            return entry
    for key in keys:
        entry = brands.get(key)
        if isinstance(entry, dict):
            return entry
    return None


def _apply_absa_sentiment_fields(
    drafts: list[EntitySignalDraft],
    brands: dict[str, Any],
    *,
    own_brand: str,
    own_absa_keys: list[tuple[str, str]],
    competitor_absa_keys: list[tuple[str, str]],
) -> None:
    by_entity_label = {draft.entity_label: draft for draft in drafts}
    own_draft = next(draft for draft in drafts if draft.entity_kind == "own")
    own_keys = _competitor_keys_by_label(own_absa_keys).get(own_draft.entity_label, [own_brand])
    score, reason = absa_brand_sentiment(_absa_entry_for_competitor(brands, own_keys))
    own_draft.sentiment_score = score
    own_draft.sentiment_reason = reason

    for output_label, keys in _competitor_keys_by_label(competitor_absa_keys).items():
        draft = by_entity_label.get(output_label)
        if draft is None:
            continue
        score, reason = absa_brand_sentiment(_absa_entry_for_competitor(brands, keys))
        draft.sentiment_score = score
        draft.sentiment_reason = reason


def apply_absa_to_drafts(
    drafts: list[EntitySignalDraft],
    response_absa: dict[str, Any],
    *,
    own_brand: str,
    own_absa_keys: list[tuple[str, str]] | None = None,
    competitor_absa_keys: list[tuple[str, str]],
    url_hosts: list[str] | None = None,
    competitors: list[CompetitorEntry] | None = None,
    text: str = "",
) -> str:
    """Merge closed-set ABSA mention flags and sentiment onto drafts; return sentiment_source."""
    source = absa_sentiment_source(response_absa)
    if source != "llm":
        degrade_absa_failure(drafts)
        return source

    brands = response_absa["brands_sentiment_absa"]
    own_keys = own_absa_keys or [(own_brand, next(d.entity_label for d in drafts if d.entity_kind == "own"))]
    _apply_absa_mentions(
        drafts,
        brands,
        own_brand=own_brand,
        own_absa_keys=own_keys,
        competitor_absa_keys=competitor_absa_keys,
        url_hosts=url_hosts,
        competitors=competitors,
        text=text,
    )
    _apply_absa_sentiment_fields(
        drafts,
        brands,
        own_brand=own_brand,
        own_absa_keys=own_keys,
        competitor_absa_keys=competitor_absa_keys,
    )
    return "llm"


def append_other_brand_drafts(
    drafts: list[EntitySignalDraft],
    response_absa: dict[str, Any],
    *,
    excluded_keys: set[str],
    text: str = "",
    url_hosts: list[str] | None = None,
) -> None:
    """Add entity_kind=other drafts from open-set ABSA (mentioned third-party brands)."""
    others = response_absa.get("other_brands_sentiment_absa")
    if not isinstance(others, dict):
        return

    existing_ids = {draft.entity_id for draft in drafts}
    for name, entry in others.items():
        label = str(name or "").strip()
        if not label or normalize_brand_key(label) in excluded_keys:
            continue
        if not isinstance(entry, dict) or not entry.get("mentioned"):
            continue
        entity_id = other_entity_id(label)
        if entity_id in existing_ids:
            continue
        score, sentiment_reason = absa_brand_sentiment(entry)
        mention_count = count_term(text, label)
        if mention_count == 0:
            mention_count = 1
        rank_hint = _rank_hint_from_absa(text, label, entry)
        if rank_hint is None:
            rank_hint = _fallback_rank_hint(text)
        drafts.append(
            EntitySignalDraft(
                entity_id=entity_id,
                entity_kind="other",
                entity_label=label,
                mentioned=True,
                mention_count=mention_count,
                rank_hint_first_index=rank_hint,
                sentiment_score=score,
                sentiment_reason=sentiment_reason,
                has_domain_link=_other_brand_has_domain_link(label, text, url_hosts or []),
            )
        )
        existing_ids.add(entity_id)


def append_candidate_mention_drafts(
    drafts: list[EntitySignalDraft],
    response_absa: dict[str, Any],
    *,
    mention_candidates: list[str] | None,
    excluded_keys: set[str],
    text: str = "",
    url_hosts: list[str] | None = None,
) -> None:
    """Fallback open-set mentions from enumeration/discovery when ABSA did not explicitly deny."""
    if not mention_candidates or not text.strip():
        return

    others = response_absa.get("other_brands_sentiment_absa")
    if not isinstance(others, dict):
        others = {}

    existing_ids = {draft.entity_id for draft in drafts}
    for raw in mention_candidates:
        label = str(raw or "").strip()
        if not label or not _is_open_candidate_label(label):
            continue
        if normalize_brand_key(label) in excluded_keys:
            continue
        if count_term(text, label) <= 0:
            continue
        if _absa_explicitly_denied(label, response_absa):
            continue
        entity_id = other_entity_id(label)
        if entity_id in existing_ids:
            continue

        entry = others.get(label)
        if isinstance(entry, dict) and entry.get("mentioned"):
            score, sentiment_reason = absa_brand_sentiment(entry)
        else:
            score = 50.0
            sentiment_reason = _evidence_snippet(text, label) or None

        mention_count = count_term(text, label) or 1
        rank_hint = _rank_hint_from_absa(text, label, entry if isinstance(entry, dict) else None)
        if rank_hint is None:
            rank_hint = first_idx_any(text, (label,))
        if rank_hint is None:
            rank_hint = _fallback_rank_hint(text)

        drafts.append(
            EntitySignalDraft(
                entity_id=entity_id,
                entity_kind="other",
                entity_label=label,
                mentioned=True,
                mention_count=mention_count,
                rank_hint_first_index=rank_hint,
                sentiment_score=score,
                sentiment_reason=sentiment_reason,
                has_domain_link=_other_brand_has_domain_link(label, text, url_hosts or []),
            )
        )
        existing_ids.add(entity_id)


def apply_response_absa_to_drafts(
    drafts: list[EntitySignalDraft],
    response_absa: dict[str, Any],
    *,
    subject: Subject | None = None,
    db: Session | None = None,
    own_brand: str,
    own_absa_keys: list[tuple[str, str]] | None = None,
    competitor_brand_names: list[str],
    competitor_absa_keys: list[tuple[str, str]],
    url_hosts: list[str] | None = None,
    competitors: list[CompetitorEntry] | None = None,
    text: str = "",
    excluded_keys: set[str] | None = None,
    mention_candidates: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Apply closed-set ABSA, append validated open-set brands, and recompute mention ranks."""
    source = apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand=own_brand,
        own_absa_keys=own_absa_keys,
        competitor_absa_keys=competitor_absa_keys,
        url_hosts=url_hosts,
        competitors=competitors,
        text=text,
    )
    if source != "llm":
        return source, response_absa

    if excluded_keys is None:
        excluded_keys = configured_brand_keys(
            own_brand=own_brand,
            competitor_brand_names=competitor_brand_names,
            competitor_absa_keys=competitor_absa_keys,
            own_absa_keys=own_absa_keys,
        )

    append_other_brand_drafts(
        drafts,
        response_absa,
        excluded_keys=excluded_keys,
        text=text,
        url_hosts=url_hosts,
    )
    candidates = mention_candidates
    if candidates is None:
        raw = response_absa.get("mention_candidates")
        candidates = raw if isinstance(raw, list) else None
    append_candidate_mention_drafts(
        drafts,
        response_absa,
        mention_candidates=candidates,
        excluded_keys=excluded_keys,
        text=text,
        url_hosts=url_hosts,
    )
    compute_mention_ranks(drafts)
    return source, response_absa
