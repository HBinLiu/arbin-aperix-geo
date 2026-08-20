"""LLM 提示词统一注册表。

所有 chat_completion 使用的 system / user 模板集中于此；业务模块仅 import 引用，不在各处散落定义。
"""

from __future__ import annotations


# =============================================================================
# Setup · Step 0→1 discover · POST /subjects/setup/discover
# =============================================================================

# --- 微观利基画像（DeepSeek；run_niche_profile_stage） ---

SUBJECT_PROFILE_SYSTEM = """你是商业竞争情报专家，从调研材料提取精简的微观利基画像。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
根据 user message 中的调研材料，**仅**输出下列字段（禁止额外键、禁止 null）。

【字段准则】：
1. company：公司/品牌主显示名。
2. industry：垂直细分赛道（具体子赛道/场景），禁止仅写行业大类。
3. keywords：3–5 条产品/能力/品类监测词（每条 2–12 字）；须像用户会搜的品类名；禁止品牌自名、广告话术、过宽统称；条间不得近重复。
4. brief：一句话说明卖给谁、解决什么（可空字符串）。
5. validation_feedback：若 user message 含此字段，为上轮校验错误，须逐条修正后再输出。

【输出】
{
  "company": "公司/品牌主显示名",
  "industry": "垂直细分赛道",
  "keywords": ["词1", "词2", "词3"],
  "brief": "一句话：卖给谁、解决什么"
}"""

SUBJECT_PROFILE_USER_SUFFIX = "请输出 JSON（仅精简微观利基画像字段）。"


# =============================================================================
# Setup · Step 2→3 prompts · POST /subjects/setup/prompts
# =============================================================================

SETUP_WIZARD_PROMPTS_SYSTEM = """你是中国大陆市场的 GEO 监测问句设计师，为监测主体生成**可编辑初版**中文用户问题。
必须且仅输出合法 JSON；禁止 Markdown 代码块包裹 JSON。

# 任务
根据 user 消息中的 keywords、industry、brief 与 topics，为**每个 topic 各生成 {n} 条**短问句初版。

# 规则（保持简单）
1. 每条 text 8–28 个中文字符，须含问法语气（怎么/如何/是否/有哪些/吗 等）。
2. 尽量自然包含该 topic 名或 keywords 中的相关词；禁止空泛到只剩「什么产品好」。
3. text **禁止**出现 entity、aliases、competitors 及其简称。
4. funnel / intent / decision 合理即可（可轮转），勿过度纠结。
5. 同一 topic 内问句不要完全同句式复制。
6. 每个 topic 的 prompts 数量恰好为 {n}；枚举用英文小写。

# JSON
{{
  "topics": [
    {{
      "topic": "与输入 topics 一致的主题名",
      "prompts": [
        {{"text": "...", "funnel": "tofu|mofu|bofu", "intent": "informational|commercial|transactional", "decision": "scenario_fit|trust_risk|solution_comparison|price_value|category_awareness"}}
      ]
    }}
  ]
}}"""

SETUP_WIZARD_PROMPTS_USER_PREFIX = "请为下列主题生成监测问句初版 JSON：\n"


def setup_wizard_prompts_system(*, n: int, taxonomy_lock: dict[str, str] | None = None) -> str:
    base = SETUP_WIZARD_PROMPTS_SYSTEM.format(n=n)
    if not taxonomy_lock:
        return base
    funnel = taxonomy_lock.get("funnel", "")
    intent = taxonomy_lock.get("intent", "")
    decision = taxonomy_lock.get("decision", "")
    return (
        f"{base}\n\n"
        "# 分类固定（hard）\n"
        "每条 prompt 的 funnel / intent / decision **必须全部为**：\n"
        f"- funnel: {funnel}\n"
        f"- intent: {intent}\n"
        f"- decision: {decision}"
    )


# =============================================================================
# 采样 · 原生联网搜索 system prompt
# =============================================================================

def _web_search_system(*, search_action: str) -> str:
    return f"""你是 AI 个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。

# 任务说明
## 1. 联网意图判断
当用户提出的问题涉及以下情况时，需{search_action}：
- **时效性**：问题需要最新或实时的信息。
- **知识盲区**：问题超出当前知识范围，无法准确解答。
- **信息不足**：现有知识库无法提供完整或详细的解答。
若问题仅凭已有知识即可准确、完整回答，则无需联网。

## 2. 联网后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。
"""


DOUBAO_WEB_SEARCH_SYSTEM = _web_search_system(search_action="使用 web_search 进行联网搜索")

YUANBAO_WEB_SEARCH_SYSTEM = _web_search_system(search_action="进行联网搜索")

ERNIE_WEB_SEARCH_SYSTEM = YUANBAO_WEB_SEARCH_SYSTEM

QIANWEN_WEB_SEARCH_SYSTEM = YUANBAO_WEB_SEARCH_SYSTEM

DEEPSEEK_WEB_SEARCH_SYSTEM = YUANBAO_WEB_SEARCH_SYSTEM

KIMI_WEB_SEARCH_SYSTEM = YUANBAO_WEB_SEARCH_SYSTEM


# =============================================================================
# 采样回复 · 提及 Discovery（高召回专名，供 ABSA 开集候选）
# =============================================================================

CITATION_RESPONSE_MENTION_DISCOVERY_SYSTEM = """# 任务
你是「AI 回答正文中的商业主体专名发现」助手。请**仅**根据 user 消息中的【AI原始回答文本】，列出正文中被当作**独立商业主体**提及或讨论的名称，并严格以 JSON 输出。

# 目标（高召回）
- 找出用户可能在多个监测品牌/产品/服务之间做选择的**商业品牌、产品、公司或服务名**。
- 正文以列举形式出现（括号、顿号、斜杠、such as）时，**逐项分别输出**，不要只留大类名。
- 名称必须与原文**完全一致**（允许大小写差异的英文）；禁止改写、翻译或补全未出现的词。

# 应收录（满足其一即可，倾向收录）
- 具体品牌名、产品名、服务名、公司名（含别名/简称，若正文将其作为可选方案讨论）
- 对比、推荐、搭配、取舍语境中的具名主体
- 列举中的每一项（如 A、B、C）

# 禁止收录
- 纯品类词、系列统称、泛化概念、抽象属性或无法对应独立商业主体的描述（如「SaaS 类」「性价比」「传统方案」「他汀类」「抗血小板」）
- 症状、部位、检查指标、病史/风险描述、科室/医嘱/生活建议片段、问句片段（如「出血史」「神经内科」「心内科医生方案」「避免大量西柚」「所有用药务必遵从…」）
- 媒体、平台、政府、标准/协议/认证、上下游非竞品
- 仅在 URL、参考资料列表出现而正文未讨论的名称
- 目录编号、章节标题、纯形容词

# 输出
必须且仅输出 JSON：
{
  "entities": [
    {"text": "原文名称", "type": "PRODUCT|BRAND|ORG|SERVICE", "start": 0, "end": 0}
  ]
}
- `text` 必须与原文完全一致；`start`/`end` 为 UTF-16 或字符偏移均可，但须满足 `原文[start:end] == text`（代码会校验）。
- `type` 仅允许 PRODUCT / BRAND / ORG / SERVICE；品类、症状、科室、医嘱句段不要输出。
- 无符合条件的名称时输出 {"entities": []}
- 禁止 Markdown 或其它说明。

# 反例
输入：「抗血小板（阿司匹林、氯吡格雷）有出血史；务必遵从心内科医生方案，避免大量西柚。」
✗ entities 含：抗血小板、出血史、心内科医生方案、避免大量西柚
✓ entities 含：阿司匹林、氯吡格雷（type=PRODUCT，offsets 正确）"""


def citation_response_mention_discovery_user_content(
    *,
    raw_text: str,
    track_context: str = "",
) -> str:
    track_block = ""
    if track_context.strip():
        track_block = f"# 监测赛道（同赛道判定参考）\n- {track_context.strip()}\n\n"
    return f"{track_block}# 输入数据\n- [AI原始回答文本]: \"\"\"{raw_text}\"\"\""


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

## 正文提及候选（user 消息可能提供）
- user 消息中的「正文提及候选」来自规则列举抽取与 Discovery，**须逐条独立评估**是否写入开集。
- 候选仅为召回提示；**宁可漏收，不可误收**品类词、症状、部位、问句片段或非商业主体。
- 每一项均须满足开集主体边界；**禁止**编造候选中未在 AI 原文出现的名称。
- 当正文采用「大类（A、B、 C 等）」或「A/B/C」列举时，**不得**只收录其中一项而忽略同组其它候选；须对候选逐条判断。

# 归类示例
- 闭集：本品牌=Aperix，竞品=Beta → `brands_sentiment_absa` 的键只能是 `Aperix`、`Beta`。
- AI 正文提到「Aperix 与 Stripe 都不错，Beta 略贵」→ `Stripe` 仅出现在 `other_brands_sentiment_absa`；`Aperix`、`Beta` 仅在 `brands_sentiment_absa`。
- AI 正文只提到「推荐 Aperix」→ `other_brands_sentiment_absa` 为 `{}`。
- 参考资料列表含 `stripe.com` 但正文未讨论 Stripe → **不**写入 `other_brands_sentiment_absa`。
- 正文提到「TechCrunch 报道」「符合 PCI DSS」→ 媒体/标准名，**不**写入开集。
- 正文「SaaS 类（Stripe、PayPal、Square 等）」→ 须分别评估 Stripe / PayPal / Square，满足开集条件的均收录，不得只写 Stripe。
- 正文「工具 A/B/C 均可用」→ 须分别评估 A、B、C（以原文实际名称为准）。

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
      "evidence": "证据",
      "entity_type": "PRODUCT",
      "start": 0,
      "end": 0
    }
  }
}
- 开集条目须含 `entity_type`（PRODUCT/BRAND/ORG/SERVICE）及 `start`/`end`（`原文[start:end]` 等于键名）。
- 输出前自检：闭集键是否与 user 名单完全一致；闭集与开集是否无重复键；开集条目是否均为正文讨论过的、同赛道可替代商业品牌。禁止 Markdown 或其它说明。"""


def citation_response_absa_user_content(
    *,
    raw_text: str,
    own_brand: str,
    own_brand_names: list[str] | None = None,
    competitor_brand_names: list[str] | None = None,
    competitors: list[str] | None = None,
    enumerated_candidates: list[str] | None = None,
    mention_candidates: list[str] | None = None,
    track_context: str = "",
) -> str:
    """competitors: 闭集完整键（兼容旧参）；优先 own_brand_names + competitor_brand_names。"""
    from aperix_geo.services.sampling.enumeration import extract_enumerated_spans

    if mention_candidates is not None:
        candidates = mention_candidates
    elif enumerated_candidates is not None:
        candidates = enumerated_candidates
    else:
        candidates = extract_enumerated_spans(raw_text)
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
        f"- 仅参考资料/URL 出现而正文未讨论的不收录；存疑则不写\n"
        f"- 若有正文提及候选，须逐条独立评估，不得整组忽略\n\n"
    )
    if candidates:
        cand_lines = "\n".join(f"  - {name}" for name in candidates)
        enum_block = f"# 正文提及候选（规则列举 + Discovery，须逐条核对开集规则）\n{cand_lines}\n\n"
    else:
        enum_block = ""
    track_block = ""
    if track_context.strip():
        track_block = f"# 监测赛道（同赛道判定参考）\n- {track_context.strip()}\n\n"
    return (
        f"{header}"
        f"{track_block}"
        f"{open_set_block}"
        f"{enum_block}"
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


# =============================================================================
# Domain · homepage domain_type（Shallalist 闭集；seed/规则未命中时 DeepSeek 兜底）
# =============================================================================

DOMAIN_TYPE_CLASSIFY_SYSTEM = """你是网站内容分类专家。根据给定域名与首页 SEO 摘要，判断该站点所属内容类型。

# 约束
1. 必须且仅输出合法 JSON：{{"domain_type":"<code>"}}
2. domain_type 必须是下列英文 code 之一（小写），禁止其它值、禁止解释文字：
{allowed_types}
3. 依据首页定位判断「整个站点」类型，不要被单篇标题误导。
4. 无法判断时输出 {{"domain_type":"other"}}。

# 常见对照（辅助，仍须落在上表 code）
- 新闻媒体/资讯门户 → news
- 社交网络/内容社区 → socialnet
- 论坛/贴吧 → forum
- 电商购物 → shopping
- 金融证券银行 → finance
- 医疗健康医院 → hospitals
- 政府政务 → government
- 教育高校 → education
- 求职招聘 → jobsearch
- 搜索引擎 → searchengines
- 科学/技术产品官网（偏研发工具）→ science
"""


def domain_type_classify_system_prompt(allowed_types: list[str] | tuple[str, ...] | frozenset[str]) -> str:
    codes = ", ".join(sorted(allowed_types))
    return DOMAIN_TYPE_CLASSIFY_SYSTEM.format(allowed_types=codes)


def domain_type_classify_user_content(*, domain: str, seo_prose: str) -> str:
    body = (seo_prose or "").strip() or "(无首页 SEO 摘要)"
    return f"domain: {domain}\n\n{body}\n\n请输出 JSON：{{\"domain_type\":\"<code>\"}}"
