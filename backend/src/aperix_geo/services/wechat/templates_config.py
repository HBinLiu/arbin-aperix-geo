"""Load WeChat template message catalog from YAML."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from aperix_geo.config import Settings, get_settings

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[4]  # .../backend


@dataclass(frozen=True, slots=True)
class TemplateField:
    keyword: str
    source: str = ""  # title | body | time | available
    value: str = ""  # literal override
    max_len: int = 0  # 0 = auto by keyword prefix


@dataclass(frozen=True, slots=True)
class TemplateDef:
    key: str
    template_id: str
    url_path: str = ""
    fields: tuple[TemplateField, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TemplateCatalog:
    jump_base_url: str
    templates: dict[str, TemplateDef]


def _default_catalog_path() -> Path:
    return _BACKEND_DIR / "config" / "wechat_templates.yaml"


def resolve_templates_path(settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    raw = (s.wechat_templates_path or "").strip()
    if not raw:
        return _default_catalog_path()
    path = Path(raw)
    if not path.is_absolute():
        path = _BACKEND_DIR / path
    return path


def _parse_field(raw: dict[str, Any]) -> TemplateField | None:
    keyword = str(raw.get("keyword") or "").strip()
    if not keyword:
        return None
    source = str(raw.get("source") or "").strip().lower()
    value = str(raw.get("value") or "")
    max_len = int(raw.get("max_len") or 0)
    return TemplateField(keyword=keyword, source=source, value=value, max_len=max_len)


def _parse_template(raw: dict[str, Any]) -> TemplateDef | None:
    key = str(raw.get("key") or "").strip()
    template_id = str(raw.get("template_id") or "").strip()
    if not key or not template_id:
        return None
    fields_raw = raw.get("data") or raw.get("fields") or []
    fields: list[TemplateField] = []
    if isinstance(fields_raw, list):
        for item in fields_raw:
            if isinstance(item, dict):
                parsed = _parse_field(item)
                if parsed is not None:
                    fields.append(parsed)
    return TemplateDef(
        key=key,
        template_id=template_id,
        url_path=str(raw.get("url_path") or "").strip(),
        fields=tuple(fields),
    )


def load_template_catalog(
    *,
    path: Path | None = None,
    settings: Settings | None = None,
) -> TemplateCatalog:
    s = settings or get_settings()
    file_path = path or resolve_templates_path(s)
    jump_env = (s.wechat_template_jump_base_url or "").strip()

    if not file_path.is_file():
        logger.warning("WeChat templates YAML missing path=%s", file_path)
        return TemplateCatalog(jump_base_url=jump_env, templates={})

    with file_path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"WeChat templates YAML root must be a mapping: {file_path}")

    jump = jump_env or str(doc.get("jump_base_url") or "").strip()
    templates: dict[str, TemplateDef] = {}
    items = doc.get("templates") or []
    if not isinstance(items, list):
        raise ValueError("WeChat templates YAML `templates` must be a list")
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = _parse_template(item)
        if parsed is None:
            continue
        templates[parsed.key] = parsed
    return TemplateCatalog(jump_base_url=jump, templates=templates)


@lru_cache(maxsize=4)
def _cached_catalog(path_str: str, jump_override: str) -> TemplateCatalog:
    # jump_override baked into cache key so env changes invalidate
    del jump_override
    return load_template_catalog(path=Path(path_str) if path_str else None)


def get_template_catalog(settings: Settings | None = None) -> TemplateCatalog:
    s = settings or get_settings()
    path = resolve_templates_path(s)
    return _cached_catalog(str(path), (s.wechat_template_jump_base_url or "").strip())


def get_template(key: str, *, settings: Settings | None = None) -> TemplateDef | None:
    catalog = get_template_catalog(settings=settings)
    return catalog.templates.get(key.strip())


def clear_template_catalog_cache() -> None:
    _cached_catalog.cache_clear()
