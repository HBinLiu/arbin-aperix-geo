"""设置向导共享工具。"""

from __future__ import annotations

from typing import Any

from aperix_geo.config import get_settings
from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.competitor.enrich import enrich_entity_aliases, resolve_summary_from_site_metadata
from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.prompts.context import entity_aliases
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.utils.net import registrable_from


def require_deepseek_api_key() -> None:
    """DeepSeek：画像、摘要、监测主题、问句生成。"""
    if not get_settings().deepseek_api_key.strip():
        raise LLMProviderError("DEEPSEEK_API_KEY is not configured")


def company_from_session(session: dict[str, Any] | None) -> str | None:
    """微观利基画像中的 company，用于写入 Subject.brand。"""
    if not session:
        return None
    profile = session.get("profile") or {}
    if not isinstance(profile, dict):
        return None
    company = str(profile.get("company") or "").strip()
    return company[:255] if company else None


def profile_summary_from_session(session: dict[str, Any] | None) -> str | None:
    if not session:
        return None
    raw = session.get("profile_summary")
    if not raw:
        return None
    text = str(raw).strip()
    return text or None


def subject_summary_from_session(session: dict[str, Any] | None) -> str:
    """Setup discover 阶段 fetch_target_homepage 写入 research_payload.site_data。"""
    if not session:
        return ""
    research = session.get("research_payload")
    if not isinstance(research, dict) or research.get("mode") != "domain":
        return ""
    site_data = research.get("site_data")
    if not isinstance(site_data, dict):
        return ""
    return resolve_summary_from_site_metadata(site_data)


def validate_confirmed_competitors(
    *,
    subject_type: str,
    competitors: list[CompetitorItem] | list[dict[str, Any]],
) -> None:
    """domain 模式需至少一个竞品域名；brand 模式需至少一个纯品牌竞品。"""
    if subject_type == "domain":
        if not any(
            (item.domain or "").strip()
            if isinstance(item, CompetitorItem)
            else str(item.get("domain") or "").strip()
            for item in competitors
        ):
            raise ValueError("按网站监测时至少需要一个竞品域名")
        return

    if not any(
        (
            (item.brand or "").strip() and not (item.domain or "").strip()
            if isinstance(item, CompetitorItem)
            else str(item.get("brand") or "").strip() and not str(item.get("domain") or "").strip()
        )
        for item in competitors
    ):
        raise ValueError("按品牌监测时至少需要一个竞品品牌")


def confirmed_competitors_from_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    """topics 步骤确认后写入 session.competitors（finalize / prompts 读取）。"""
    if not session.get("confirmed_competitors_hash"):
        raise ValueError("setup session missing confirmed competitors")
    raw = session.get("competitors")
    if not isinstance(raw, list) or not raw:
        raise ValueError("setup session missing confirmed competitors")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(dict(item))
    if not out:
        raise ValueError("setup session missing confirmed competitors")
    return out


def competitor_labels_from_session(session: dict[str, Any]) -> list[str]:
    """prompts 生成用：domain 模式取域名，brand 模式取品牌名。"""
    competitors = confirmed_competitors_from_session(session)
    subject_type = str(session.get("subject_type") or "")
    if subject_type == "domain":
        return [
            str(item.get("domain") or "").strip()
            for item in competitors
            if str(item.get("domain") or "").strip()
        ]
    return [
        str(item.get("brand") or "").strip()
        for item in competitors
        if str(item.get("brand") or "").strip()
    ]


def subject_aliases_from_session(session: dict[str, Any]) -> list[str]:
    """从 session 推导 Subject.aliases（profile.company 与 entity 差异）。"""
    entity = str(session.get("target") or "").strip()
    if not entity:
        return []
    profile = profile_from_dict(session.get("profile") or {})
    configured = list(session.get("aliases") or [])
    return entity_aliases(
        entity=entity,
        configured=configured,
        profile_company=str(profile.get("company") or ""),
    )


def _site_metadata_from_session(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None
    research = session.get("research_payload")
    if not isinstance(research, dict) or research.get("mode") != "domain":
        return None
    site_data = research.get("site_data")
    return site_data if isinstance(site_data, dict) else None


def enrich_subject_aliases(
    *,
    brand: str,
    domain: str,
    session: dict[str, Any],
    heads: dict[str, SiteHead] | None = None,
) -> list[str]:
    """Setup finalize：从 session/profile + site_data + head SEO 合并主体 aliases。"""
    base = subject_aliases_from_session(session)

    reg = registrable_from(domain)
    if not reg:
        return base

    site_metadata = _site_metadata_from_session(session)
    head = heads.get(reg) if heads else None
    return enrich_entity_aliases(
        brand=brand,
        domain=reg,
        existing=base,
        head=head,
        site_metadata=site_metadata,
    )
