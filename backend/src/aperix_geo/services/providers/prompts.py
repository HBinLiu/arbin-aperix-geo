"""LLM 提示词统一注册表。

所有 chat_completion 使用的 system / user 模板集中于此；业务模块仅 import 引用，不在各处散落定义。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aperix_geo.services.competitor.types import NicheProfile


# =============================================================================
# Setup · Step 0→1 discover · POST /subjects/setup/discover
# =============================================================================

# --- 微观利基画像（DeepSeek；run_niche_profile_stage） ---

SUBJECT_PROFILE_SYSTEM = """你是商业竞争情报专家，专注从调研材料提取该主体所在垂直赛道的微观利基结构化画像。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
根据 user message 中的调研材料，**仅**输出微观利基画像结构化字段。

【字段准则】：
1. company：公司/品牌主显示名。
2. industry：垂直细分赛道（具体子赛道/场景），禁止仅写行业大类或空泛统称。
3. features：2–3 个核心技术/产品能力词或短语。
4. customers：精准付费或使用群体。
5. topic_lexicon：监测关键词词表（4 类，每类 2–4 条），**贯穿**主题规划与提示词生成。
   - category_terms：**产品/能力头词**（4–8 字为佳；可直接作为 topic name；**至少 5 条**，供 5 个监测主题绑定）；须像该赛道真实用户会搜的产品/能力/品类名；**禁止**照搬调研材料中的广告宣传、排名宣称、规模数量类话术；禁止竞品对标/对比分析/选型等场景词
   - scenario_terms / audience_terms / pain_terms：**长尾修饰词**（场景、客群、痛点；与核心词组合成问句）
   - category 内不得近重复（如「品牌提及率」与「品牌提及率分析」只保留更具体一条）
   - 每条 ≥4 字；禁止品牌自名、过宽行业词、决策维度词。
6. search_queries：4–5 条**完整长尾问句范例**（每条须**完整包含** category_terms 中至少 1 个核心词原文，并叠加 topic_lexicon 中至少 1 个修饰词；**5 条去掉 core 与 modifiers 后句法骨架须互异**；≥8 字）。须像该赛道用户**向 AI 口述**的短问句（含怎么/如何/是否/吗 等），**从调研材料与 industry 归纳**；至少约 1/3 条须含问法语气；禁止仅用修饰词造句、禁止自创新核心词、禁止 5 条同一骨架换词。
7. validation_feedback：若 user message 含此字段，为上轮校验错误，须逐条修正后再输出。

【输出】
必须且仅输出 JSON（禁止额外键、禁止 null、禁止 Markdown 代码块）：
{
  "company": "公司/品牌主显示名",
  "industry": "垂直细分赛道",
  "features": ["能力词1", "能力词2"],
  "customers": "精准付费或使用群体（一句或短语）",
  "topic_lexicon": {
    "category_terms": ["核心词A", "核心词B", "核心词C", "核心词D", "核心词E"],
    "scenario_terms": ["场景修饰词1", "场景修饰词2"],
    "audience_terms": ["客群修饰词1"],
    "pain_terms": ["痛点修饰词1"]
  },
  "search_queries": [
    "核心词A场景修饰词1客群修饰词1",
    "核心词B场景修饰词2痛点修饰词1",
    "核心词C客群修饰词1场景修饰词1",
    "核心词A痛点修饰词1场景修饰词2",
    "核心词B场景修饰词1客群修饰词1"
  ]
}"""

SUBJECT_PROFILE_USER_SUFFIX = "请输出 JSON（仅微观利基画像字段）。"


# --- 豆包联网竞品发现（discover_competitors_via_doubao） ---

COMPETITOR_DOUBAO_DISCOVER_DOMAIN_SYSTEM = """你是竞品研究分析师。联网搜索直接竞品，仅输出合法 JSON（禁止 Markdown）。

输出：{"competitors": [{"brand": "品牌名", "website_url": "https://...", "aliases": []}]}

规则：
- 每条须含 brand、website_url；website_url **必须**为 http:// 或 https:// 开头的完整 URL（含主机，可含路径），**禁止**仅填裸域名（如 example.com）
- aliases 为别名/简称（可空数组，勿重复 brand）
- 按市场认可度降序；排除监测主体自身及媒体/聚合/政府/纯品类词
- 无结果：{"competitors": []}"""

COMPETITOR_DOUBAO_DISCOVER_BRAND_SYSTEM = """你是竞品研究分析师。联网搜索直接竞品，仅输出合法 JSON（禁止 Markdown）。

输出：{"competitors": [{"brand": "品牌名", "website_url": "https://...", "aliases": []}]}

规则：
- 每条须含 brand（必填）；有官网则填 website_url，**必须**为 http:// 或 https:// 开头的完整 URL，**禁止**仅填裸域名；无官网可省略 website_url
- aliases 为别名/简称（可空数组，勿重复 brand）
- 按市场认可度降序；排除监测主体自身及媒体/聚合/政府/纯品类词
- 无结果：{"competitors": []}"""


def competitor_doubao_discover_domain_user_content(
    *,
    target: str,
    website_url: str,
    profile: NicheProfile,
    region: str,
    language: str,
) -> str:
    company = str(profile.get("company") or target).strip() or target
    industry = str(profile.get("industry") or "—").strip() or "—"
    subject = website_url.strip() or target.strip()
    return (
        f"subject_type=domain\n"
        f"主体：{subject}\n"
        f"赛道：{industry}\n"
        f"公司：{company}\n"
        f"市场：{region}（{language}）\n"
        f"请联网搜索，输出 competitors JSON（≥5 条，含 brand+website_url；website_url 须为完整 http(s) URL，禁止裸域名），排除主体自身。"
    )


def competitor_doubao_discover_brand_user_content(
    *,
    target: str,
    profile: NicheProfile,
    region: str,
    language: str,
) -> str:
    company = str(profile.get("company") or target).strip() or target
    industry = str(profile.get("industry") or "—").strip() or "—"
    customers = str(profile.get("customers") or "—").strip() or "—"
    return (
        f"subject_type=brand\n"
        f"主体品牌：{target}\n"
        f"赛道：{industry}\n"
        f"公司：{company}\n"
        f"客户：{customers}\n"
        f"市场：{region}（{language}）\n"
        f"请联网搜索，输出 competitors JSON（≥5 条，含 brand；有官网则填完整 http(s) URL，禁止裸域名），排除主体自身。"
    )


# --- 竞品交叉验算打分（run_cross_validate；enrich 仅用 head，无 LLM） ---

COMPETITOR_CROSS_VALIDATE_SYSTEM = """你是垂直赛道竞争分析师，负责对监测主体与候选竞品做交叉比对并打分。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
对「目标企业 A」与「候选企业 B」做交叉比对并打分（0–10）。

评分维度（综合为 score）：
1. 客户重合度：目标用户/购买决策链是否高度重叠？
2. 功能重合度：核心卖点与解决的痛点是否一致？
3. 体量匹配度：是否处于相同生态位（非大厂无关子业务、非媒体/测评/资讯站）？

A 与 B 均含 domain、title、description 及可选 head 元数据；A 另含 company/industry/features/customers/topic_lexicon/search_queries（微观画像）。

硬性降分规则（应给 0–4 分）：
- B 是媒体、博客、知乎专栏、新闻、排行榜、测评聚合站
- B 是大厂的一个不相干子业务或泛平台入口
- B 与 A 客单价/体量相差超过 10 倍且不在同一细分赛道
- 元数据过少无法判断时给 3–5 分并说明不确定

高分规则（8–10 分）：
- 仅当 B 能够直接抢走 A 的核心客户、在同一垂直品类正面竞争时

输出 JSON：{"scores": [{"domain": "b.com", "score": 9, "reason": "一句话理由"}, ...]}"""


def cross_validate_user_content(*, target_json: str, candidates_json: str) -> str:
    return (
        "目标企业 A：\n"
        f"{target_json}\n\n"
        "候选企业列表（请对每个 B 打分）：\n"
        f"{candidates_json}"
    )


# =============================================================================
# Setup · Step 1→2 topics · POST /subjects/setup/topics
# =============================================================================

# --- 主题规划（run_topic_generation_stage） ---

SUBJECT_TOPIC_PLAN_SYSTEM = """# Role
你是 GEO 监测规划专家与监测问句架构师。根据 user message 中的 niche_profile、keyword_plan、topic_guidance 与 competitor_scenarios，输出监测主题簇与种子问句矩阵。

必须且仅输出合法 JSON；禁止 Markdown 代码块或多余解释。

# Goal
- **Topic name**：由系统在输出后绑定为 `keyword_plan.core_keywords` 前 5 条；LLM 可填占位 name，但**重点在 seed**。
- **Seed query** = 真实用户会向 AI 口述的长尾问句：含本 topic 的 core_keyword，自然带入 scenario/audience/pain 修饰词；decision 体现在 metadata，**不要**写进 topic name。

# user message 字段
- keyword_plan.long_tail_examples：**首要仿写对象**（句法气质与多样性的标杆，不是只换 core 的填槽模板）
- keyword_plan.core_keywords / modifiers：核心词与修饰词词表
- topic_keyword_map：各 core 的 preferred_modifiers（**参考**错开修饰词，勿机械拼接原文）
- topic_guidance.seed_style_rules / forbidden_seed_shapes：句法多样性硬约束
- validation_feedback：上轮校验错误（若有），须逐条修正
- competitor_scenarios：仅供理解赛道，**不得**写入 name 或 seed text

# 维度标签（seed 必填）
1. intent：`informational` | `commercial` | `transactional`
2. funnel：`tofu` | `mofu` | `bofu`
3. decision：`category_awareness` | `solution_comparison` | `trust_risk` | `price_value` | `scenario_fit`

# Topic 约束
1. 条数：5 个 topic_clusters；name 占位即可（系统绑定 core_keyword）。
2. 5 条 seed 矩阵须覆盖不同 core_keyword；禁止近重复 topic 名、禁止竞品对标/对比分析等泛词作 topic。
3. 不得含主体/竞品名；topic name 不得采用问句形态。

# Seed 约束（hard）
1. 每 topic **至少 5 条** seed，8–28 字；每条须**完整包含**本 topic 的 core_keyword。
2. **句法多样（最高优先级）**
   - 同一 topic 内：5 条 seed 去掉 core 与 modifiers 后**句法骨架须互异**；decision 亦须互异。
   - **跨 topic 禁止模板铺量**：不得 5 个 topic 共用同一组固定句式，仅替换 core_keyword（如每条 topic 都写「平台中如何提升→角色怎么监测→影响大吗→需要多少预算→表现怎么查」这类五句式）。
   - 写前通读 `long_tail_examples`：每个 topic 的 seed 应**分散仿写不同范例**的问法，而非复制同一套五句式。
3. **口述问句感**：须像用户向 AI 提问（怎么/如何/是否/吗/？ 等自然出现即可）；禁止名词短语标题体、禁止百科/导购栏目标题。
4. **修饰词**：从 keyword_plan.modifiers 或 long_tail_examples **自然嵌入**；禁止为凑 preferred_modifiers 原文而机械连写。
5. 不得点名品牌/竞品；对比类用「主流方案」「头部平台」等泛指。

# 反模板自检（输出前必做）
- 若 5 个 topic 的 seed 逐条对比，仅 core 不同而前后缀相同 → **必须重写**。
- 若同一 topic 内多条 seed 仅换 decision 标签而句法相同 → **必须重写**。
- 优先让每条 seed 的**开头/疑问重心/句末**与其他 seed 明显不同。

# Output Format
{
  "topic_clusters": [
    {
      "name": "主题名",
      "seed_queries": [
        {
          "text": "问句",
          "intent": "informational|commercial|transactional",
          "funnel": "tofu|mofu|bofu",
          "decision": "category_awareness|solution_comparison|trust_risk|price_value|scenario_fit"
        }
      ]
    }
  ]
}"""

SUBJECT_TOPIC_PLAN_USER_SUFFIX = (
    "请输出 JSON。须满足 keyword_plan 与 topic_guidance；"
    "重点：每个 topic 5 条 seed 句法互异，5 个 topic 之间不得复用同一套句式换 core；"
    "先读 long_tail_examples 再写 seed。"
    "若有 validation_feedback 须全部修正。"
)


# --- 主体 Markdown 摘要（run_profile_summary_stage；监测主题生成后） ---

SUBJECT_PROFILE_SUMMARY_SYSTEM = """你是企业情报文档撰写专家，负责在竞品搜索完成后为监测主体编写完整 Markdown 摘要（供用户审阅与后续 GEO 监测配置）。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
根据 user message 中的 niche_profile、region、language、competitors（已确认竞品，含 brand/domain），编写完整 profile_summary。
摘要须与 niche_profile 一致；可确认章节依据调研材料；竞争相关章节须结合 competitors 撰写，勿编造未列出的竞品。

【Markdown 结构】（二级标题必须严格使用下列中文，按顺序输出）：
# {品牌/公司主显示名}
## 概述
## 核心能力
4–6 条，格式为 * **标签：** 说明
## 产品与服务
3–5 条主要产品线/服务线/方案线
## 目标用户
3–5 条，格式为 * **用户群：** 场景说明
## 市场定位
1–3 条 bullet，结合 competitors 写差异化定位
## 竞品
仅列出 user message 中的 competitors；每条格式 * **品牌名**（domain）：竞争关系或差异说明（domain 为空时可省略括号）
无竞品时输出：* **暂无：** 本轮搜索未发现符合条件的竞品
## 核心价值
## 独家能力
2–4 条 bullet，结合竞品突出差异
## 客户痛点
2–4 条 bullet
## 理想客户画像
一行 ICP 描述
## 决策触发点
一句引号包裹的典型触发问句
## 地域与合规
* **主要市场：** …（结合 region）
* **合规要求：** …

【输出】
必须且仅输出 JSON：{"profile_summary": "完整 Markdown 字符串（换行用 \\n）"}"""

SUBJECT_PROFILE_SUMMARY_USER_SUFFIX = "请输出 JSON（仅 profile_summary）。"


# =============================================================================
# Setup · Step 2→3 prompts · POST /subjects/setup/prompts
# =============================================================================

SETUP_WIZARD_PROMPTS_SYSTEM = """你是中国大陆市场的 GEO 监测问句设计师，为监测主体设计可在 AI 搜索平台长期追踪的中文**真实用户问题**。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
根据 user 消息 JSON 中的 keyword_plan、topic_keyword_map 与 topic_clusters，为**每个 topic 各生成 {n} 条**问句，用于评估该主体核心词在 AI 回答中的可见度。

# user 消息字段
- keyword_plan：core_keywords（核心词）、modifiers（修饰词）、long_tail_examples（长尾范例，**须仿写其句法**）
- topic_keyword_map：每个 topic 的 core_keyword 与 preferred_modifiers（**参考**错开修饰词，非每条 hard 必填）
- topic_clusters：含 name、seed_queries（**必须**优先改写/扩展，不可忽略）
- entity / aliases / competitors：仅供理解，**不得**写入问句 text
- industry / features / customers：背景参考，问句须锚定 core_keyword 而非仅 industry
- validation_feedback：上轮校验错误（若有），须逐条修正
- prompts_per_topic：等于 {n}
- exclude_prompts：已生成问题，禁止重复

# 核心词硬要求
1. 每条 prompt 的 text **必须完整包含** topic_keyword_map 中该 topic 的 core_keyword。
2. 每条 prompt **必须**由同 topic 的某条 seed 改写/扩展（保留 seed 的核心语义片段）。
3. 修饰词从 keyword_plan.modifiers 或 seed 自然带入即可；**禁止** 5 个 topic 共用同一后缀句式。
4. 去掉 core 与 modifiers 后，**不同 topic 的问句骨架不得相同**（禁止「换 core、句式不变」）。
5. 禁止仅 industry 级泛化问句（如「什么产品好」「哪个方案好」）而无 core_keyword。

# 问句语气（hard）
- 每条 text **须**含问法语气（怎么/如何/是否/有哪些/吗 等），像用户对 AI 口述，而非名词短语或栏目标题。
- **不得**用同一后缀骨架换 core/decision 批量铺量。

# 问法丰富度（每 topic {n} 条须同时满足）
1. 同一 topic 内须覆盖 **≥4 种不同句法骨架**（以 long_tail_examples 与 seed 为依据）。
2. 同一 topic 内 **≥4 条**须含问法语气（怎么/如何/是否/有哪些/吗 等），像用户对 AI 口述。
3. 禁止同一 topic 内多条仅替换修饰词而句法完全相同。

# 品牌名称禁令
- text 禁止出现 entity、aliases、competitors 及其简称、域名；对比类用「主流方案」「头部平台」等泛指。

# 组合级覆盖（全库 {n}×topic 数 条合计）
- funnel 合计（营销漏斗逐层递减，目标比 tofu:mofu:bofu = 5:3:2，即约 50% / 30% / 20%）
- intent 合计：informational 30–40% / commercial 30–40% / transactional 20–35%
- decision 合计：须覆盖 **≥4 种**

# 句式铁律
1. 每条 8–28 个中文字符；像用户直接问 AI 的短句。
2. 禁止机械复读 topic 名全文；禁止论坛口语前缀。

# JSON 返回规范
1. 必须且只能输出一个严格合法的标准 JSON 对象。
2. 结构：
{{
  "topics": [
    {{
      "topic": "与 topic_clusters.name 一致的主题名",
      "prompts": [
        {{
          "text": "问句",
          "funnel": "tofu|mofu|bofu",
          "intent": "informational|commercial|transactional",
          "decision": "category_awareness|solution_comparison|trust_risk|price_value|scenario_fit"
        }}
      ]
    }}
  ]
}}
3. funnel / intent / decision 必须使用上述英文小写枚举；每个 topic 的 prompts 数量恰好为 {n}。"""

SETUP_WIZARD_PROMPTS_USER_PREFIX = "请生成初始监测提示词：\n"


def setup_wizard_prompts_system(*, n: int, taxonomy_lock: dict[str, str] | None = None) -> str:
    base = SETUP_WIZARD_PROMPTS_SYSTEM.format(n=n)
    if not taxonomy_lock:
        return base
    funnel = taxonomy_lock.get("funnel", "")
    intent = taxonomy_lock.get("intent", "")
    decision = taxonomy_lock.get("decision", "")
    return (
        f"{base}\n\n"
        "# 分类固定（hard，覆盖上文「组合级覆盖」）\n"
        "每条 prompt 的 funnel / intent / decision **必须全部为**：\n"
        f"- funnel: {funnel}\n"
        f"- intent: {intent}\n"
        f"- decision: {decision}"
    )


# --- Setup 问句风格软评（evaluate_query_style_via_llm） ---

QUERY_STYLE_JUDGE_SYSTEM = """你是 GEO 监测问句质量评审员。根据 user message 中的问句批次，判断它们是否像真实用户向 AI 口述的短问句，而非名词短语堆叠或栏目标题体。

必须且仅输出合法 JSON；禁止 Markdown 代码块或多余解释。

# 评审标准（语义判断，禁止维护行业后缀黑名单）
1. **口述问句感**：像在问 AI 具体问题（可有怎么/如何/是否/吗 等，但不强制枚举词表）；纯名词短语、百科条目名、导购栏目标题为不合格。
2. **非模板铺量**：同一组内多条仅换核心词/修饰词而句法完全相同，或跨 topic 复用同一后缀骨架，为不合格。
3. **自然组合**：core + modifier 应自然嵌入问句，而非机械连写后挂固定尾巴。
4. **参考范例**：若提供 long_tail_examples，合格问句应与其句法气质相近（多样、口语、非标题体）。

# user message 字段
- stage：`profile`（search_queries）| `topics`（seed_queries）| `prompts`
- groups：每组含 label、queries；topics/prompts 阶段含 topic
- long_tail_examples：可选，profile 阶段生成的长尾范例

# 输出
{"pass": true, "feedback": []}
或
{"pass": false, "feedback": ["具体、可执行的修正说明（中文，供下一轮 LLM 生成参考）", "..."]}

feedback 须具体指出哪类问题（标题体/模板重复/不够像问句），并给出改写方向；勿仅复读规则。"""

QUERY_STYLE_JUDGE_USER_SUFFIX = "请输出 JSON（仅 pass 与 feedback）。"


# =============================================================================
# 采样 · 原生联网搜索 system prompt（各平台引用格式不同）
# =============================================================================

DOUBAO_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需使用 web_search 进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中明确引用来源，引用格式为：
  `[1] (URL地址)`

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""

YUANBAO_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中用角标引用来源（如 `[1]`、`[2]`），与 search_info 列表对应。

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""

ERNIE_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中用角标引用来源，格式为 `^[1]^`、`^[2]^` 等。

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""

QIANWEN_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中用角标引用来源，格式为 `[ref_1]`、`[ref_2]` 等。

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""


DEEPSEEK_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中用角标引用来源，格式为 `[1]`、`[2]` 等。

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""


KIMI_WEB_SEARCH_SYSTEM = """你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需进行联网搜索：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。

## 3. 引用已搜索资料
- 当使用联网搜索的资料时，在正文中用角标引用来源，格式为 `[1]`、`[2]` 等。

## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
  1. [资料标题](URL地址1)
  2. [资料标题](URL地址2)
"""


# =============================================================================
# 采样回复 · 回复级 ABSA（AI 原文情感，每条回复一次）
# =============================================================================

CITATION_RESPONSE_ABSA_SYSTEM = """# 任务
你是 ABSA（基于属性/实体的观点挖掘）专家。请**仅**根据【AI原始回答文本】，对监测范围内的品牌与正文中讨论的同赛道潜在竞品做情感分析，并严格以 JSON 输出。

# 评分标准 (1 到 100，50 为完全中立)
- 100 (强烈推荐)：AI将其作为首选推荐，且几乎全是赞美。
- 75 (正面提及)：AI肯定了其部分优势，或将其列入推荐清单。
- 50 (完全中立)：纯客观数据或事实陈述，无明显偏向。
- 25 (负面提及)：明确指出了产品、服务或技术上的缺陷或局限性。
- 1 (强烈踩贬)：明确建议不要选择，或在对比中垫底。
* 注意：大模型用“硬核数据”背书视同正面；用“传统、历史悠久、遵循早期规范”委婉劝退视同负面。

# 核心约束
1. 必须严格以 JSON 格式输出，不要包含任何前后解释文字。
2. `mentioned`：品牌是否在【AI原始回答文本】中被提及或讨论。
3. `score` / `evidence`：**必须且只能**来自【AI原始回答文本】，不得使用引用页正文。
4. 未在 AI 原文出现的品牌：`mentioned=false`，`score=null`，`evidence=""`。
5. 禁止编造 AI 原文未出现的品牌、观点或证据。

# 两个输出对象的分工（必须严格遵守，禁止混用）

## brands_sentiment_absa — 闭集（固定填表）
- **键必须且仅能**来自 user 消息中的「本品牌」与「竞品列表」；不得新增、删减或改写键名。
- 即使某品牌在 AI 原文未出现，也必须输出该键，并设 `mentioned=false`。
- **禁止**将本品牌或任一竞品写入 `other_brands_sentiment_absa`。

## other_brands_sentiment_absa — 开集（同赛道潜在竞品，精准收录）
- **仅**收录 AI **正文**中明确讨论、对比或推荐的、与闭集品牌**同赛道可替代**的商业品牌/产品/公司。
- 必须同时满足：
  1. 在正文（非仅参考资料列表、脚注、URL 域名）中被当作**独立品牌主体**提及；
  2. AI 对其有评价、对比、推荐或取舍语境（可给出 `score` / `evidence`）；
  3. 与闭集本品牌/竞品属于同一产品或服务赛道，用户可能在其间做选择。
- **宁可漏收，不可误收**；无法确认是同赛道商业品牌时，一律不写入。
- 闭集品牌无论以全称、简称、别名、域名形式出现，**一律只写入** `brands_sentiment_absa`，**不得**重复写入此处。
- **禁止**写入以下非开集主体（即使被提及）：
  - 媒体/新闻站、内容平台、搜索引擎、社交平台、论坛社区
  - 政府机构、行业标准/协议/认证名称
  - 上下游供应商、渠道商、合作伙伴、客户案例公司
  - 纯行业品类词、泛化技术名词、无法对应独立商业品牌的产品型号/系列名
  - 目录导航、测评聚合站、百科/问答站点
  - 仅在参考资料列表或 URL 中出现、正文未讨论的品牌名
- 若 AI 原文未出现符合条件的额外商业品牌，必须输出空对象 `{}`。

# 归类示例
- 闭集：本品牌=Aperix，竞品=Beta → `brands_sentiment_absa` 的键只能是 `Aperix`、`Beta`。
- AI 正文提到「Aperix 与 Stripe 都不错，Beta 略贵」→ `Stripe` 仅出现在 `other_brands_sentiment_absa`；`Aperix`、`Beta` 仅在 `brands_sentiment_absa`。
- AI 正文只提到「推荐 Aperix」→ `other_brands_sentiment_absa` 为 `{}`。
- 参考资料列表含 `stripe.com` 但正文未讨论 Stripe → **不**写入 `other_brands_sentiment_absa`。
- 正文提到「TechCrunch 报道」「符合 PCI DSS」→ 媒体/标准名，**不**写入开集。

# 输入数据（user 消息按以下结构提供）
- 本品牌、竞品列表（闭集完整名单）
- [AI原始回答文本]: \"\"\"{ai_raw_response}\"\"\"

# 输出 JSON 格式
{
  "brands_sentiment_absa": {
    "[闭集-本品牌名称]": {
      "mentioned": true,
      "score": 90,
      "evidence": "从【AI原始回答文本】中抽取的直接证据"
    },
    "[闭集-竞品名称]": {
      "mentioned": false,
      "score": null,
      "evidence": ""
    }
  },
  "other_brands_sentiment_absa": {
    "[开集-其它商业品牌名]": {
      "mentioned": true,
      "score": 75,
      "evidence": "证据"
    }
  }
}
- 输出前自检：闭集键是否与 user 名单完全一致；闭集与开集是否无重复键；开集条目是否均为正文讨论过的、同赛道可替代商业品牌。禁止 Markdown 或其它说明。"""


def citation_response_absa_user_content(
    *,
    raw_text: str,
    own_brand: str,
    own_brand_names: list[str] | None = None,
    competitor_brand_names: list[str] | None = None,
    competitors: list[str] | None = None,
) -> str:
    """competitors: 闭集完整键（兼容旧参）；优先 own_brand_names + competitor_brand_names。"""
    own_keys = list(own_brand_names or [])
    if not own_keys and own_brand.strip():
        own_keys = [own_brand.strip()]
    comp_keys = list(competitor_brand_names or [])
    if competitors and not own_brand_names and not competitor_brand_names:
        closed_keys = list(dict.fromkeys([name for name in competitors if str(name).strip()]))
    else:
        closed_keys = list(dict.fromkeys([*own_keys, *comp_keys]))
    own_lines = "\n".join(f"  - {name}" for name in own_keys if str(name).strip()) or "  - （无）"
    comp_lines = "\n".join(f"  - {name}" for name in comp_keys if str(name).strip()) or "  - （无）"
    closed_text = "、".join(closed_keys) if closed_keys else own_brand
    header = (
        f"# 闭集名单（brands_sentiment_absa 的键必须且仅能是下列名称，顺序不限）\n"
        f"- 本品牌（canonical）：{own_brand}\n"
        f"- 本品牌闭集键（含别名/域名）：\n{own_lines}\n"
        f"- 竞品闭集键：\n{comp_lines}\n"
        f"- 闭集完整键集合：[{closed_text}]\n\n"
    )
    open_set_block = (
        f"# 开集规则（other_brands_sentiment_absa）\n"
        f"- 精准收录：仅填 AI 正文中被讨论/对比/推荐、与闭集同赛道可替代的商业品牌\n"
        f"- 不在闭集 [{closed_text}] 内；闭集品牌任何写法都不得写入此处\n"
        f"- 仅参考资料/URL 出现而正文未讨论的不收录；存疑则不写\n\n"
    )
    return (
        f"{header}"
        f"{open_set_block}"
        f"# 输入数据\n"
        f'- [AI原始回答文本]: """{raw_text}"""'
    )


# =============================================================================
# Knowledge · graph extract · Celery knowledge.extract_subject
# =============================================================================

KNOWLEDGE_GRAPH_EXTRACT_SYSTEM = """你是品牌知识图谱抽取器。根据资料抽取实体与关系，必须且仅输出合法 JSON（禁止 Markdown 代码块）。

# 允许的节点 type（禁止自创）
brand | product | audience | pain | differentiator | competitor | scenario | proof

含义：
- brand：本品（通常与输入 brand.primary_name 一致；可省略，系统会补）
- product：产品线 / 核心功能 / 服务套餐
- audience：目标人群 / ICP
- pain：痛点 / 待解决问题
- differentiator：差异化卖点
- competitor：资料中出现的竞品名（勿臆造）
- scenario：使用场景 / 用例
- proof：证据背书（数据、案例、奖项、认证）

# 允许的边 type（禁止自创）
offers | serves | solves | differentiates_by | competes_with | used_in | part_of | supported_by

方向约定：
- offers: brand/product → product
- serves: brand/product → audience
- solves: brand/product → pain
- differentiates_by: brand/product → differentiator
- competes_with: brand → competitor
- used_in: product → scenario
- part_of: 子功能/产品 → 上级 product 或 brand
- supported_by: differentiator/product/brand → proof

# 规则
1. 只抽取资料中有依据的内容；不确定则不写。
2. from / to 优先用节点 label（与 nodes[].label 一致）；也可写 source 中的 brand 名。
3. source_ids 必须来自输入 sources[].source_id；无把握可省略（系统会回填）。
4. evidence 为原文短摘录，≤120 字；confidence 为 0–1 小数。
5. 控制规模：nodes ≤ 40，edges ≤ 60；合并近义 label。
6. 禁止输出 nodes/edges 以外的顶层键。

# 输出
{
  "nodes": [
    {"type": "product", "label": "可见度监测", "aliases": [], "source_ids": ["uuid"], "confidence": 0.9}
  ],
  "edges": [
    {
      "type": "solves",
      "from": "品牌名或产品名",
      "to": "痛点名",
      "source_ids": ["uuid"],
      "evidence": "原文摘录",
      "confidence": 0.85
    }
  ]
}"""

KNOWLEDGE_GRAPH_EXTRACT_USER_SUFFIX = "请仅输出 JSON（nodes + edges）。"