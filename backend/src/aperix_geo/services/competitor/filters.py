"""竞品发现：SearXNG 候选池预排除（媒体/平台/聚合站，节省交叉验算成本）。"""

from __future__ import annotations

# 主流媒体、UGC、百科、大厂泛域 — 交叉验算也会打低分，但提前跳过更省 LLM/抓取
SKIP_DOMAINS: frozenset[str] = frozenset(
    {
        "google.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "wikipedia.org",
        "amazon.com",
        "apple.com",
        "microsoft.com",
        "github.com",
        "youtube.com",
        "reddit.com",
        "quora.com",
        "medium.com",
        "zhihu.com",
        "baike.baidu.com",
        "baidu.com",
        "36kr.com",
        "huxiu.com",
        "sohu.com",
        "ifeng.com",
        "163.com",
        "sina.com.cn",
        "sina.com",
        "toutiao.com",
        "mp.weixin.qq.com",
        "weixin.qq.com",
        "xiaohongshu.com",
        "douyin.com",
        "bilibili.com",
        "cnblogs.com",
        "csdn.net",
        "jianshu.com",
        "weibo.com",
        "qq.com",
        "qcc.com",
        "tianyancha.com",
        "extrabux.cn",
        "bacaoo.com",
        "eastmoney.com",
        "10jqka.com.cn",
        "10jqka.com",
        "155.cn",
    },
)

# 测评/比价聚合、政府站、应用下载站等（hostname 子串匹配）
AGGREGATOR_MARKERS: tuple[str, ...] = (
    "g2.com",
    "capterra.com",
    "trustpilot",
    "alternativeto",
    "producthunt.com",
    "crunchbase.com",
    "paymentcloud",
    "forbes.com",
    "zhuanlan.zhihu",
    "zhihu.com/question",
    "zhihu.com/pin",
    ".gov.cn",
    "wandoujia.com",
    "crsky.com",
    "91danji.com",
    "155.cn",
    "cr173.com",
    "danji100.com",
    "gamehome.tv",
    "xdowns.com",
    "sm.cn/blm",
    "100ec.cn",
    "openi.cn",
)


def should_skip_domain(host: str) -> bool:
    """是否应从候选池排除（主域名已归一后调用）。"""
    if host in SKIP_DOMAINS:
        return True
    return any(marker in host for marker in AGGREGATOR_MARKERS)
