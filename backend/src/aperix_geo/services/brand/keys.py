"""Normalized brand keys for closed-set vs open-set ABSA exclusion."""

from __future__ import annotations

from aperix_geo.services.brand.resolve import normalize_brand_key


def configured_brand_keys(
    *,
    own_brand: str = "",
    own_match_names: list[str] | None = None,
    competitor_brand_names: list[str] | None = None,
    competitor_absa_keys: list[tuple[str, str]] | None = None,
    own_absa_keys: list[tuple[str, str]] | None = None,
    subject_aliases: list[str] | None = None,
    competitor_aliases: list[str] | None = None,
) -> set[str]:
    """Normalized keys for configured own/competitor brands (incl. aliases)."""
    keys: set[str] = set()
    for name in [own_brand, *(own_match_names or []), *(subject_aliases or [])]:
        if name.strip():
            keys.add(normalize_brand_key(name))
    for absa_key, _output_label in own_absa_keys or []:
        if absa_key.strip():
            keys.add(normalize_brand_key(absa_key))
    for name in competitor_brand_names or []:
        if name.strip():
            keys.add(normalize_brand_key(name))
    for alias in competitor_aliases or []:
        if str(alias).strip():
            keys.add(normalize_brand_key(str(alias)))
    for absa_key, _output_label in competitor_absa_keys or []:
        if absa_key.strip():
            keys.add(normalize_brand_key(absa_key))
    return keys
