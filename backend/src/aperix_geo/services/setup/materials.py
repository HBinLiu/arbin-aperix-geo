"""品牌模式 Setup 资料合并与充足性校验。"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError

MIN_BRAND_CORPUS_CHARS = 300

_INSUFFICIENT_PROFILE_MESSAGE = (
    "根据现有资料无法生成完整的微观利基画像，请补充更完整的品牌介绍后重试"
    "（建议覆盖：品牌定位、核心业务、目标客群、差异化优势，不少于 300 字）。"
)

_INSUFFICIENT_CORPUS_MESSAGE = (
    "品牌介绍与上传资料不足，请补充更完整的品牌介绍"
    "（建议覆盖：品牌定位、核心业务、目标客群、差异化优势，不少于 300 字）。"
)


@dataclass(frozen=True)
class BrandMaterials:
    brand_intro: str
    upload_files: tuple[dict[str, Any], ...]
    website_url: str


@dataclass(frozen=True)
class DiscoverProfileInputs:
    """discover 画像阶段输入：域名/品牌模式共用。"""

    website_url: str
    user_corpus: str
    homepage_text: str
    homepage_metadata: tuple[tuple[str, str], ...]
    materials_fingerprint: str = ""
    brand_intro: str = ""
    upload_files: tuple[dict[str, Any], ...] = ()
    materials_saved: bool = False

    def profile_hash_value(
        self,
        *,
        subject_type: str,
        target: str,
        region: str,
        language: str,
    ) -> str:
        from aperix_geo.services.setup.cache.profile import profile_hash

        return profile_hash(
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            website_url=self.website_url,
            materials_fingerprint=self.materials_fingerprint,
        )

    @property
    def homepage_metadata_dict(self) -> dict[str, str]:
        return dict(self.homepage_metadata)


def resolve_brand_materials(session: dict[str, Any] | None) -> BrandMaterials:
    if not session:
        return BrandMaterials(brand_intro="", upload_files=(), website_url="")
    uploads = session.get("upload_files") or []
    if not isinstance(uploads, list):
        uploads = []
    return BrandMaterials(
        brand_intro=str(session.get("brand_intro") or "").strip(),
        upload_files=tuple(item for item in uploads if isinstance(item, dict)),
        website_url=str(session.get("website_url") or "").strip(),
    )


def build_user_corpus(*, brand_intro: str = "", upload_files: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None) -> str:
    parts: list[str] = []
    intro = brand_intro.strip()
    if intro:
        parts.append(intro)
    for item in upload_files or ():
        text = str(item.get("extracted_text") or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def effective_corpus_chars(*, user_corpus: str, homepage_text: str = "") -> int:
    combined = f"{user_corpus.strip()}\n{homepage_text.strip()}".strip()
    return len(re.sub(r"\s+", "", combined))


def materials_fingerprint(materials: BrandMaterials) -> str:
    payload = {
        "brand_intro": materials.brand_intro,
        "website_url": materials.website_url,
        "upload_files": [
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "extracted_text": str(item.get("extracted_text") or ""),
            }
            for item in materials.upload_files
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def assert_brand_corpus_sufficient(
    *,
    user_corpus: str,
    homepage_text: str = "",
) -> None:
    if effective_corpus_chars(user_corpus=user_corpus, homepage_text=homepage_text) >= MIN_BRAND_CORPUS_CHARS:
        return
    raise MaterialsInsufficientError(_INSUFFICIENT_CORPUS_MESSAGE)


def is_niche_profile_sufficient(profile: NicheProfile) -> bool:
    industry = profile.get("industry", "").strip()
    if not industry or industry == "未知行业":
        return False
    features = profile.get("features", "").strip()
    customers = profile.get("customers", "").strip()
    search_queries = profile.get("search_queries", "").strip()
    category_terms = profile.get("category_terms", "").strip()
    if not search_queries and not category_terms:
        return False
    if not features and not customers:
        return False
    return True


def assert_niche_profile_sufficient(profile: NicheProfile) -> None:
    if is_niche_profile_sufficient(profile):
        return
    raise MaterialsInsufficientError(_INSUFFICIENT_PROFILE_MESSAGE)
