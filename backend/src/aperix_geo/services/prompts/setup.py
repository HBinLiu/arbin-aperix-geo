"""设置向导：初始提示词生成（LLM）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

PROMPTS_PER_TOPIC = 10

_SYSTEM_PROMPT = """# 角色
你是一个精通 AEO（回答引擎优化）和商业决策搜索行为学的顶尖专家。

# 任务
根据用户提供的【监测主题】，站在专业选型评审者的角度，裂变出共 {n} 个用于测试大模型品牌推荐心智的原生提示词（Prompts）。

# 🛑 铁律（严禁违反）
1. 拒绝机械拼接：严禁在提示词中复读【监测主题】的完整字眼。必须用行业通称、技术代称、痛点词或上下游关联词做自然替换。
2. 严禁社区口语：全面禁止出现论坛、闲聊式词汇（如“想问下、听说、求推荐”）。
3. 专家评审语态：全面采用严谨、客观、批判性的商务审视语气。必须高频使用“如何证实、是否存在风险、代际差异、技术壁垒”等深度疑问句。

# 📊 5大意图维度
必须将 {n} 个提示词完美均分至以下 5 个维度（每个维度恰好 {per_dimension} 条），对照示例的极致精简句式泛化：
1. 寻源推荐（Discovery）：寻找解决方案。例：“目前市场主流方案有哪些？”
2. 痛点门槛（Value/Pain）：考核成本与风险。例：“该方案的落地成本与长期风险如何？”
3. 横向拉踩（Comparative）：纠结竞品与选型。例：“垂直工具相比通用大厂核心优势在哪？”
4. 风控安全（Risk/Trust）：质疑安全与合规。例：“如何确保该第三方工具的数据绝对合规？”
5. 进阶长尾（Advanced）：针对高并发深度场景。例：“面对高并发冲击系统底层能否稳定支撑？”

# JSON 返回规范（极其重要）
1. 必须且只能输出一个严格合法的标准 JSON 对象，严禁包含任何 Markdown 标记（如 ```json）、前导解释或后置总结。
2. 结构必须严格保持如下：
{{"topics":[{{"topic":"输入的主题名","prompts":["问句1", "问句2", "问句3"]}}]}}"""


def _normalize_prompts(raw: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= PROMPTS_PER_TOPIC:
            break
    return out


def generate_setup_prompts(
    *,
    entity: str,
    topics: list[str],
    industry: str = "",
    core_features: str = "",
    target_customers: str = "",
    competitors: list[str] | None = None,
    region: str = "CN",
    language: str = "zh-CN",
) -> list[dict[str, Any]]:
    """每个主题返回至多 PROMPTS_PER_TOPIC 条 LLM 生成的提示词。"""
    cleaned_topics = [t.strip() for t in topics if t.strip()]
    if not cleaned_topics:
        return []

    entity = entity.strip() or "本品牌"
    competitors = [c.strip() for c in (competitors or []) if c.strip()]

    user_payload = {
        "entity": entity,
        "region": region,
        "language": language,
        "industry": industry,
        "core_features": core_features,
        "target_customers": target_customers,
        "competitors": competitors[:8],
        "topics": cleaned_topics,
        "prompts_per_topic": PROMPTS_PER_TOPIC,
    }

    per_dimension = max(1, PROMPTS_PER_TOPIC // 5)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT.format(n=PROMPTS_PER_TOPIC, per_dimension=per_dimension)},
        {
            "role": "user",
            "content": f"请生成初始监测提示词：\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}",
        },
    ]
    text, _, latency_ms = chat_completion(messages, temperature=0.4, json_mode=True)
    data = extract_json_object(text)
    rows = data.get("topics")
    if not isinstance(rows, list):
        raise ValueError("missing topics array")

    by_name = {
        str(row.get("topic") or "").strip(): row
        for row in rows
        if isinstance(row, dict) and str(row.get("topic") or "").strip()
    }
    result: list[dict[str, Any]] = []
    for topic in cleaned_topics:
        row = by_name.get(topic) or next(
            (by_name[k] for k in by_name if k in topic or topic in k),
            None,
        )
        raw_prompts = row.get("prompts") if isinstance(row, dict) else []
        prompts = _normalize_prompts(raw_prompts if isinstance(raw_prompts, list) else [])
        result.append({"topic": topic, "prompts": prompts})

    logger.info(
        "设置向导提示词: entity=%r topics=%d %.0fms",
        entity,
        len(result),
        latency_ms,
    )
    return result
