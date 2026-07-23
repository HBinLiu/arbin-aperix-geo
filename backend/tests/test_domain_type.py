"""Tests for domain type taxonomy and seed classification."""

from __future__ import annotations

from aperix_geo.services.domain.seeds import seed_domain_type
from aperix_geo.services.domain.taxonomy import DOMAIN_TYPES, normalize_domain_type


def test_normalize_domain_type_accepts_shallalist_codes() -> None:
    assert normalize_domain_type("News") == "news"
    assert normalize_domain_type("unknown-xyz") == "other"
    assert normalize_domain_type("") == "other"
    assert normalize_domain_type(None) == "other"
    assert "socialnet" in DOMAIN_TYPES
    assert "other" in DOMAIN_TYPES


def test_seed_domain_type_common_hosts() -> None:
    assert seed_domain_type("zhihu.com") == "socialnet"
    assert seed_domain_type("wikipedia.org") == "education"
    assert seed_domain_type("jd.com") == "shopping"
    assert seed_domain_type("example-unknown-brand.test") == ""


def test_seed_domain_type_cn_hosts() -> None:
    assert seed_domain_type("csdn.net") == "forum"
    assert seed_domain_type("36kr.com") == "news"
    assert seed_domain_type("haodf.com") == "hospitals"
    assert seed_domain_type("autohome.com.cn") == "automobile"
    assert seed_domain_type("zhipin.com") == "jobsearch"
    assert seed_domain_type("eastmoney.com") == "finance"
    # eTLD+1：公众号归到 qq.com
    assert seed_domain_type("mp.weixin.qq.com") == "socialnet"


def test_seed_domain_type_suffix_and_heuristics() -> None:
    assert seed_domain_type("news.sina.com.cn") == "news"
    # *.gov* 仅靠启发式，不进 seed 表
    assert seed_domain_type("gov.cn") == "government"
    assert seed_domain_type("nhc.gov.cn") == "government"
    assert seed_domain_type("www.nhc.gov.cn") == "government"
    assert seed_domain_type("beijing.gov.cn") == "government"
    assert seed_domain_type("example.gov") == "government"
    assert seed_domain_type("metro.go.jp") == "government"
    assert seed_domain_type("foo.govt.nz") == "government"
    assert seed_domain_type("bar.gob.mx") == "government"
    assert seed_domain_type("baz.gouv.fr") == "government"
    assert seed_domain_type("service.gc.ca") == "government"
    assert seed_domain_type("nato.int") == "government"
    assert seed_domain_type("nhs.uk") == "hospitals"
    assert seed_domain_type("school.sch.uk") == "education"
    assert seed_domain_type("school.k12.cn") == "education"
    assert seed_domain_type("techcrunch.com") == "news"
    assert seed_domain_type("indeed.com") == "jobsearch"
    assert seed_domain_type("webmd.com") == "hospitals"
    assert seed_domain_type("cs.stanford.edu") == "education"
    assert seed_domain_type("www.tsinghua.edu.cn") == "education"
    assert seed_domain_type("ox.ac.uk") == "education"
    assert seed_domain_type("mygovhelp.com") == ""  # 非整标签 gov，不误伤
    assert seed_domain_type("random-brand.example") == ""
