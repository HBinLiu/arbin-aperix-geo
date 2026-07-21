"""Curated registrable-domain → Shallalist domain_type seed map."""

from __future__ import annotations

# eTLD+1 → Shallalist code (high-traffic CN / global citation hosts)
DOMAIN_TYPE_SEEDS: dict[str, str] = {
    # social / UGC
    "zhihu.com": "socialnet",
    "weibo.com": "socialnet",
    "xiaohongshu.com": "socialnet",
    "douban.com": "socialnet",
    "facebook.com": "socialnet",
    "twitter.com": "socialnet",
    "x.com": "socialnet",
    "linkedin.com": "socialnet",
    "instagram.com": "socialnet",
    "qq.com": "socialnet",
    # forum
    "reddit.com": "forum",
    "discord.com": "forum",
    "stackoverflow.com": "forum",
    "csdn.net": "forum",
    "juejin.cn": "forum",
    "segmentfault.com": "forum",
    # video / recreation
    "bilibili.com": "recreation",
    "youtube.com": "recreation",
    "douyin.com": "recreation",
    "tiktok.com": "recreation",
    "iqiyi.com": "movies",
    "youku.com": "movies",
    # news / media
    "36kr.com": "news",
    "huxiu.com": "news",
    "thepaper.cn": "news",
    "sina.com.cn": "news",
    "sohu.com": "news",
    "163.com": "news",
    "cnn.com": "news",
    "bbc.com": "news",
    "nytimes.com": "news",
    "reuters.com": "news",
    "caixin.com": "news",
    "jiemian.com": "news",
    "medium.com": "news",
    "sspai.com": "news",
    # education / encyclopedia
    "wikipedia.org": "education",
    "coursera.org": "education",
    "edx.org": "education",
    "mooc.cn": "education",
    # shopping
    "taobao.com": "shopping",
    "tmall.com": "shopping",
    "jd.com": "shopping",
    "amazon.com": "shopping",
    "amazon.cn": "shopping",
    "pinduoduo.com": "shopping",
    "suning.com": "shopping",
    # finance
    "eastmoney.com": "finance",
    "xueqiu.com": "finance",
    "bloomberg.com": "finance",
    # government
    "gov.cn": "government",
    # search
    "google.com": "searchengines",
    "bing.com": "searchengines",
    "sogou.com": "searchengines",
    "baidu.com": "searchengines",
    # webmail
    "gmail.com": "webmail",
    "outlook.com": "webmail",
    # downloads / tech hosting
    "github.com": "downloads",
    # hospitals / health
    "haodf.com": "hospitals",
    "dxy.cn": "hospitals",
}


def seed_domain_type(domain: str) -> str:
    key = (domain or "").strip().lower()
    if not key:
        return ""
    if key in DOMAIN_TYPE_SEEDS:
        return DOMAIN_TYPE_SEEDS[key]
    parts = key.split(".")
    for i in range(1, len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in DOMAIN_TYPE_SEEDS:
            return DOMAIN_TYPE_SEEDS[candidate]
    return ""
