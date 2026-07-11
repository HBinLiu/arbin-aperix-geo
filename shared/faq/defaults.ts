/** 静态 FAQ 默认内容的 HTML 片段（仅开发者维护，不含用户输入） */

export function faqP(...paragraphs: string[]): string {
  return paragraphs.map((text) => `<p>${text}</p>`).join("");
}

export function faqBody(body: {
  paragraphs: string[];
  bullets?: string[];
  closingParagraphs?: string[];
}): string {
  let html = faqP(...body.paragraphs);
  if (body.bullets?.length) {
    html += `<ul>${body.bullets.map((text) => `<li>${text}</li>`).join("")}</ul>`;
  }
  if (body.closingParagraphs?.length) {
    html += faqP(...body.closingParagraphs);
  }
  return html;
}

/** 与 `shared/faq/index.ts` 的 `Faq` 一致（避免 defaults → index 循环，便于 Payload seed 直链） */
export type FaqDefault = {
  question: string;
  answerHtml: string;
  label?: string;
};

export const homeFaqDefaults: FaqDefault[] = [
  {
    question: "GEO 和 SEO 有什么区别？",
    answerHtml: faqP("SEO 针对搜索引擎排名进行优化。GEO（生成引擎优化）针对 AI 模型的引用和推荐进行优化。两者对于全面的品牌可见性都至关重要。"),
  },
  {
    question: "{{siteName}} 与其他 GEO 工具有什么不同？",
    answerHtml: faqP("我们关注信任，而不仅仅是可见性。我们为您展示排名位置、情感分析和可执行的建议，而不仅仅是提及次数。"),
  },
  {
    question: "支持哪些 AI 模型？",
    answerHtml: faqP("国内主流大模型：豆包、DeepSeek、通义千问、腾讯元宝、Kimi、文心一言均已支持 —— 更多模型正在持续添加中。"),
  },
  {
    question: "多久能看到效果？",
    answerHtml: faqP("趋势可见性需要 2-4 周，可落地洞察需要 4-8 周。AI 模型的更新速度与搜索引擎不同。我们同样也提供针对中大型企业的GEO/SEO优化服务，帮助您直接达成流量/AI可见度的目标，直接交付结果。"),
  },
];

export const pricingFaqDefaults: FaqDefault[] = [
  {
    label: "提示词",
    question: "提示词代表什么？",
    answerHtml: faqBody({
      paragraphs: [
        "提示词是你希望 AI 回答的业务问题，例如「哪个 GEO 工具适合中小企业」或「某品类推荐哪家品牌」。",
        "如果您每天在 3 个模型上运行 50 个 Prompt，持续 30 天，那么总共会追踪 4,500 条回答。",
      ],
    }),
  },
  {
    label: "品牌",
    question: "我可以把提示词分配到多个品牌中吗？",
    answerHtml: faqBody({
      paragraphs: [
        "可以。每个品牌拥有独立的提示词库与监测配置，你可以在订阅额度内创建多个品牌，分别追踪不同产品线的 AI 可见性。",
        "团队席位支持多人协作，同一品牌下的提示词、竞争对手与采样结果对团队成员共享。",
      ],
    }),
  },
  {
    label: "方案",
    question: "后续可以调整使用量或更换方案吗？",
    answerHtml: faqBody({
      paragraphs: [
        "可以。随着使用量增长，您可以随时切换方案。企业版也支持增加自定义模型包和专属服务。",
      ],
    }),
  },
  {
    label: "计费",
    question: "是否提供年付或季付折扣？",
    answerHtml: faqBody({
      paragraphs: ["提供。年付或季付可享受额外优惠，非常适合持续开展 GEO 运营的团队。"],
    }),
  },
];

export const answerEngineInsightsFaqDefaults: FaqDefault[] = [
  {
    label: "方法",
    question: "{{siteName}} 是如何分析 AI 是如何「回答」我的品牌的？",
    answerHtml: faqBody({
      paragraphs: [
        "{{siteName}} 基于真实 AI 平台（如豆包、DeepSeek、通义千问等）的真实回复结果，系统化追踪品牌在 AI 回答中的可见度、提及方式、排序位置与引用来源等。",
        "这不是模拟或预测，而是对 AI 在真实用户提问场景中如何理解、引用与呈现你的品牌的真实还原，从而帮助你判断当前 AI 对品牌的实际认知状态。",
      ],
    }),
  },
  {
    label: "差异",
    question: "AI 可见度数据和传统 SEO 排名有什么不同？",
    answerHtml: faqBody({
      paragraphs: [
        "传统 SEO 关注的是网页在搜索结果中的位置，而 AI 可见度关注的是：在 AI 直接给出的答案里，是否提到你、如何提到你、是否引用你。",
        "{{siteName}} 分析的是 AI Answer 层的表现，包括 Visibility、Share of Voice、Citation 和情绪倾向等，帮助您理解在 AI 搜索与问答场景中，品牌是否真正「被看见、被信任、被推荐」。",
      ],
    }),
  },
  {
    label: "竞争",
    question: "我可以看到和竞争对手在同一个 AI 问题下的对比吗？",
    answerHtml: faqBody({
      paragraphs: [
        "可以。{{siteName}} 基于真实用户 Prompt，在同一个问题场景中，直观展示您与竞争对手的是否被 AI 提及、出现顺位、声量份额与引用来源差异。",
        "这能帮助您快速识别：哪些高价值问题已经被对手占据，哪些仍是可突破的机会点。",
      ],
    }),
  },
  {
    label: "引用",
    question: "AI 引用我的品牌时，依赖的是哪些网站或内容？",
    answerHtml: faqBody({
      paragraphs: [
        "{{siteName}} 会拆解 AI 回答背后的引用来源结构，包括引用的具体域名与页面、内容类型（官网、博客、新闻、社媒、电商 / 购物平台等），以及不同 AI 平台的引用偏好差异。",
        "通过这些洞察，您可以明确：哪些内容正在影响 AI 的判断逻辑，以及哪些引用入口是可以被补齐、替代或强化的。",
      ],
    }),
  },
  {
    label: "行动",
    question: "{{siteName}} 的数据能直接指导我接下来该怎么优化吗？",
    answerHtml: faqBody({
      paragraphs: [
        "可以，而且这是核心价值之一。{{siteName}} 不仅展示结果，还会帮助您识别 AI 偏好的内容结构与主题方向，判断 GEO 资源该优先投向哪些平台、问题或页面，并提前发现潜在的负面情绪或认知偏差风险。",
        "让您从「看到差距」，进一步走到「知道下一步该做什么」。",
      ],
    }),
  },
];

export const findTopicsIdeasFaqDefaults: FaqDefault[] = [
  {
    label: "方法论",
    question: "{{siteName}} 是如何识别 AI 机会？",
    answerHtml: faqBody({
      paragraphs: [
        "{{siteName}} 并不是基于假设或关键词预测，而是基于真实 AI 回答、真实提示词和真实引用结构进行分析。",
        "我们通过对比品牌与竞争对手在 AI 回答中的覆盖深度、排序位置和引用来源等信息，识别：",
      ],
      bullets: [
        "尚未被充分覆盖的高价值问题",
        "被竞争对手忽视但 AI 明确偏好的场景",
        "能够快速建立 AI 可见度优势的切入点",
      ],
      closingParagraphs: ["让机会来自 AI 的实际判断逻辑，而不是主观推测。"],
    }),
  },
  {
    label: "竞争",
    question: "能看到被竞品占据的机会吗？",
    answerHtml: faqBody({
      paragraphs: ["可以，而且这是 {{siteName}} 的核心能力之一。", "平台会清晰展示："],
      bullets: [
        "在哪些提示词下，AI 已经频繁引用竞争对手",
        "竞争对手依赖的是哪些内容、信源或外链",
        "当前品牌在哪些高价值场景中仍然「缺席」",
      ],
      closingParagraphs: [
        "这些洞察可以直接指导用户：优先补什么内容、先抢哪个问题、从哪里切入最容易见效。",
      ],
    }),
  },
  {
    label: "覆盖范围",
    question: "{{siteName}} 的机会分析涵盖社交媒体、电子商务和社区场景吗？",
    answerHtml: faqBody({
      paragraphs: [
        "可以。{{siteName}} 不只分析官网和博客，还会系统性拆解 AI 回答中引用的：社交媒体内容、问答社区与论坛、电商平台和产品页面。",
        "通过这些分析，你可以发现：",
      ],
      bullets: [
        "哪些社区讨论正在影响 AI 的判断",
        "哪些产品场景和提示词更容易被 AI 推荐",
        "哪些平台和区域具备更高的增长潜力",
      ],
      closingParagraphs: ["从而把 GEO 机会延伸到内容、社媒、电商和增长协同。"],
    }),
  },
  {
    label: "执行",
    question: "在发现机会后，{{siteName}} 能否帮我真正「执行」？",
    answerHtml: faqBody({
      paragraphs: [
        "可以。{{siteName}} 的目标不是只告诉你「机会在哪」，而是帮助你把机会转化为可衡量的增长，包括：",
      ],
      bullets: [
        "基于高价值提示词直接生成内容",
        "明确哪些外链和信源最值得优先投入",
        "持续监控机会是否转化为 AI 可见度和引用提升",
      ],
      closingParagraphs: ["让每一次优化，都围绕 AI 是否真的开始更多地提及你。"],
    }),
  },
  {
    label: "可扩展性",
    question: "{{siteName}} 的机会是否适合大规模执行而非一次性优化？",
    answerHtml: faqBody({
      paragraphs: [
        "是的。{{siteName}} 将机会设计为可复制、可扩展的增长单元，而不是单点建议。",
        "当某一类提示词、内容结构或信源类型被验证有效后，你可以将同样的逻辑快速扩展到：",
      ],
      bullets: ["更多相似问题", "不同平台或区域", "不同产品线或解决方案"],
      closingParagraphs: [
        "这使得优化不再是零散动作，而是可以持续放大的系统性增长策略。",
      ],
    }),
  },
];

export const promptExplorerFaqDefaults: FaqDefault[] = [
  {
    label: "定义",
    question: "什么是查询扇出？",
    answerHtml: faqBody({
      paragraphs: [
        "查询扇出指的是 AI 在回答一个问题时，为生成最终答案所展开的研究路径，包括拆解出的子查询数量以及引用的信息来源数量。",
        "在 {{siteName}} 中，查询扇出基于 RAG（检索增强生成）架构和多智能体工作流，模拟 AI 的查询拆解与并行检索过程，记录子查询数量、引用来源及趋势变化，真实还原 AI 的研究路径。",
      ],
    }),
  },
  {
    label: "重要性",
    question: "查询扇出越高代表什么？",
    answerHtml: faqBody({
      paragraphs: [
        "查询扇出越高，说明 AI 需要拆解更多子问题并参考更多来源，问题背后的研究深度与决策复杂度也更高。",
        "在 {{siteName}} 中，高扇出主题通常意味着更高的决策价值。如果品牌在这些问题中的引用率较低，往往是优先布局的关键机会。",
      ],
    }),
  },
  {
    label: "区别",
    question: "提示词与查询扇出和关键词分析有什么不同？",
    answerHtml: faqBody({
      paragraphs: [
        "关键词分析关注「用户搜索什么」；查询扇出关注「AI 如何研究问题」。",
        "{{siteName}} 通过模拟 AI 的拆解与检索流程，展示子查询结构、引用来源分布及平台差异，让你看到的不只是搜索量，而是 AI 的决策链路。",
      ],
    }),
  },
  {
    label: "应用",
    question: "如何利用查询扇出找到高价值机会？",
    answerHtml: faqBody({
      paragraphs: [
        "高价值机会通常是「高扇出 + 低品牌引用」的提示词。",
        "{{siteName}} 会自动识别这些研究深度高但品牌缺席的场景，帮助你优先布局内容与产品页面，提高在 AI 回答链路中的可见度与引用概率。",
      ],
    }),
  },
  {
    label: "决策",
    question: "查询扇出可以帮助我做哪些决策？",
    answerHtml: faqBody({
      paragraphs: [
        "查询扇出可用于判断问题是否值得投入、制定内容与 GEO 优先级，以及提前预判用户的下一步提问方向，帮助品牌在 AI 回答链路中提前占位。",
      ],
    }),
  },
];

export const contentCreationFaqDefaults: FaqDefault[] = [
  {
    label: "定位",
    question: "{{siteName}} 内容创作和传统 AI 写作工具有什么不同？",
    answerHtml: faqBody({
      paragraphs: [
        "传统 AI 写作工具关注「写得快」，而 {{siteName}} 关注「写得能被找到、被引用」。",
        "平台从选题阶段就结合 SEO 与 GEO 信号，确保内容同时面向搜索排名与 AI 回答场景进行结构设计。",
      ],
    }),
  },
  {
    label: "流程",
    question: "从选题到发布，{{siteName}} 如何指导每一步？",
    answerHtml: faqBody({
      paragraphs: ["完整工作流覆盖四个阶段："],
      bullets: [
        "发现：基于 SEO + GEO 数据识别高潜力话题",
        "大纲：生成结构化、易引用的内容框架",
        "创作：在实时优化建议下完成撰写",
        "发布：导出至 WordPress、Notion 等 CMS",
      ],
      closingParagraphs: ["让团队不再在多个工具之间切换，而是在同一流程中完成策略与执行。"],
    }),
  },
  {
    label: "优化",
    question: "内容如何同时兼顾 Google 排名和 AI 引用？",
    answerHtml: faqBody({
      paragraphs: [
        "{{siteName}} 会从关键词覆盖、实体识别、话题深度、语义结构、易引用格式与可读性等维度进行优化。",
        "写作过程中持续给出评分与修复建议，例如补充 FAQ、添加数据点、优化章节层级等，帮助内容在发布前达到 SEO 与 GEO 双重标准。",
      ],
    }),
  },
  {
    label: "语言",
    question: "是否支持多语言内容创作？",
    answerHtml: faqBody({
      paragraphs: [
        "支持。{{siteName}} 覆盖 20 多种语言的内容创作与优化，帮助团队在不同市场以母语级质量产出内容。",
        "同一套 SEO/GEO 优化逻辑可应用于多语言场景，确保全球内容策略保持一致。",
      ],
    }),
  },
];

export const monitorFaqDefaults: FaqDefault[] = [
  {
    question: "监测是如何进行的？",
    answerHtml: faqP("我们使用与行业相关的提示词持续向 AI 平台发起查询，并追踪品牌在回答中被提及、引用和推荐的情况。"),
  },
  {
    question: "数据更新频率是多久？",
    answerHtml: faqP("我们的监测每天运行，对于 AI 平台讨论您品牌的重大变化，我们会提供实时提醒。"),
  },
  {
    question: "我可以与竞争对手进行对比吗？",
    answerHtml: faqP("可以，我们的竞争情报功能可以展示您在所有已监测平台中，与竞争对手在 AI 可见性方面的对比情况。"),
  },
];

