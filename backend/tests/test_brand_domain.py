"""Tests for brand domain resolution helpers."""

from __future__ import annotations

from aperix_geo.services.brand.domain import (
    domain_plausibly_matches_brand,
    extract_domain_from_text_for_brand,
    other_entity_id,
)


def test_other_entity_id_stable() -> None:
    assert other_entity_id("Stripe") == other_entity_id("stripe")
    assert other_entity_id("Stripe").startswith("other:")


def test_domain_plausibly_matches_brand() -> None:
    assert domain_plausibly_matches_brand("stripe.com", "Stripe")
    assert not domain_plausibly_matches_brand("zgswcn.com", "透镜GEO")


def test_extract_domain_from_nearby_url() -> None:
    text = "推荐 Stripe（https://stripe.com/payments）用于跨境收款。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", ["https://stripe.com/payments"])
    assert domain == "stripe.com"


def test_extract_domain_from_host_match() -> None:
    text = "也可以访问 stripe.com 了解详情。"
    domain = extract_domain_from_text_for_brand(text, "Stripe", [])
    assert domain == "stripe.com"


def test_extract_domain_prefers_citation_url_over_text_score() -> None:
    text = "DeepRank 的情感得分是 96.8，详情见 https://deeprank.ai/about。"
    domain = extract_domain_from_text_for_brand(text, "DeepRank", ["https://deeprank.ai/about"])
    assert domain == "deeprank.ai"


def test_extract_domain_ignores_absa_score_near_brand() -> None:
    text = "DeepRank 的情感得分是 96.8，整体表现不错。"
    domain = extract_domain_from_text_for_brand(text, "DeepRank", [])
    assert domain == ""


def test_extract_domain_ignores_decimal_without_letters() -> None:
    text = "ImpetaAI（99.5）在 GEO 领域表现突出。"
    domain = extract_domain_from_text_for_brand(text, "ImpetaAI", [])
    assert domain == ""
