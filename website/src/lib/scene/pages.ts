import { mergeFaqs, resolveFaqDefaults, type Faq } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import { sceneFaqDefaultsBySlug } from "@shared/faq/defaults";
import {
  SCENE_SLUGS,
  sceneFaqPage,
  type SceneSlug,
} from "@shared/faq/pages";
import { SCENE_PAGE_SEO } from "@shared/seo/defaults/scene";
import { toPageSeo } from "@/lib/seo";
import { resolveSiteCopyDeep } from "@/lib/site";
import { SCENE_PILLAR_IMAGES } from "@/lib/scene/feature";
import { sceneCtaBySlug } from "@/lib/scene/cta";
import type { SceneContent } from "@/lib/scene/types";

const pillarImages = SCENE_PILLAR_IMAGES;

const productLaunchPage = resolveSiteCopyDeep({
  slug: "product-launch" as const,
  seo: toPageSeo(SCENE_PAGE_SEO["product-launch"]),
  badge: "使用场景",
  hero: {
    title: "产品发布成功之道：从第一天起获得 AI 引用",
    description:
      "当 AI 不知道新产品存在时，它们就会在沉默中消亡。传统的发布方式需要数周时间等待百度抓取并排名。但如果 AI 缺乏关于您产品的数据，您在 AI 推荐中就是「不可见」的——这将错失 40% 的潜在曝光机会。确保您的发布能获得即时的 AI 引用、品类提及和客户发现。",
    ctaLabel: "开始使用",
    ctaHref: "/auth/register",
  },
  diagnostic: {
    title: "产品发布盲区",
    userQuestion: "最适合初创公司的营销自动化工具有哪些？",
    summary: "正在运行诊断... 发现了关键的发布准备缺口：",
    gaps: [
      {
        code: "GAP_01",
        label: "旧玩法",
        description:
          "传统发布：开发产品、发布、等待百度索引、获取流量。这一套在过去 20 年一直有效。",
      },
      {
        code: "GAP_02",
        label: "AI 不可见",
        description:
          "新现实：AI 没有关于您新产品的训练数据。您在 AI 推荐中可能会消失数月之久。",
      },
      {
        code: "GAP_03",
        label: "发布静默",
        description:
          "65% 的新产品在发布前 3 个月获得的 AI 提及量为零 —— 即使它们在百度上排名很好。",
      },
      {
        code: "GAP_04",
        label: "收入损失",
        description:
          "影响：您会错失 40% 的潜在发布收入，因为 AI 无法向正在寻找解决方案的用户推荐您。",
      },
    ],
  },
  why: {
    title: "为什么 AI 发布有所不同",
    cards: [
      {
        icon: "timeline" as const,
        text: "百度时间线：百度需要 2-4 周来抓取、索引并排名您的新产品页面。侧重 SEO。",
      },
      {
        icon: "ai-orbit" as const,
        text: "AI 的要求：需要多个来源、上下文和信任信号，才会将您的产品纳入推荐。",
      },
      {
        icon: "lightbulb" as const,
        text: "验证问题：AI 会问：「这是一个真实的产品吗？有真实用户在用吗？他们推荐吗？有第三方验证吗？」",
      },
      {
        icon: "lightbulb" as const,
        text: "双重策略：您需要一套与传统 SEO 发布并行的协同 AI 发布策略。",
      },
    ],
  },
  solution: {
    title: "针对 AI 的发布策略",
    pillars: [
      {
        title: "预发布阶段（前 30 天）",
        description:
          "创作 AI 可读的内容：结构化的产品页、使用案例、FAQ 板块。通过合作伙伴证言和预发布报道建立初步的信任信号。",
        image: pillarImages.competitiveSet,
      },
      {
        title: "发布日战术",
        description:
          "协同的多渠道发布：新闻稿 + 博客 + 社交媒体 + 合作伙伴内容。在 24 小时内发布第一个客户成功故事。",
        image: pillarImages.competitiveIdentify,
      },
      {
        title: "发布后加速（第 1-30 天）",
        description:
          "监测 AI 提及情况，通过详细指南扩展内容，放大社交证明。目标在第 4 周达到 10-20% 的提及率。",
        image: pillarImages.competitiveGap,
      },
    ],
  },
  workflows: {
    title: "产品发布案例研究",
    items: [
      {
        title: "新型 AI 驱动的 SEO 工具发布",
        icon: "chart-rising" as const,
        challenge: "预发布：准备了 8 个对比指南、3 个合作伙伴证言、具有清晰定位的结构化产品页。",
        action:
          "发布日：新闻稿 + 博客 + 社交媒体同步发声。第 1 周：0% AI 提及（预期内）。第 2 周：发布了 2 个详细的使用案例指南。",
        result:
          "第 4 周：AI 提及率达到 24%。第 3 个月：推荐率达到 38%，成为所属品类中排名第 2 的被推荐工具。",
      },
      {
        title: "SaaS 平台市场进入",
        icon: "network-nodes" as const,
        challenge: "进入拥挤的项目管理领域。20 多个老牌竞争对手已拥有强大的 AI 存在感。",
        action:
          "聚焦于尚未被充分服务的细分市场：「创意 SEO/GEO 服务商」。发布了 5 个针对该行业的案例研究，并与设计社区合作。",
        result: "在 2 个月内，成为「针对创意 SEO/GEO 服务商的项目管理」查询的首选推荐工具。",
      },
    ],
  },
  metrics: {
    title: "发布成功指标",
    cards: [
      {
        icon: "chart-pie" as const,
        title: "AI 提及增长速度",
        description: "提及率占比每周的增长速度如何？",
      },
      {
        icon: "chart-no-axes-column" as const,
        title: "品类存在感",
        description: "您出现在多少场「最佳产品」对话中？",
      },
      {
        icon: "sentiment" as const,
        title: "情感评分",
        description: "提及内容是正向、中性还是负向？",
      },
      {
        icon: "rocket" as const,
        title: "AI 转化率",
        description: "追踪来自 AI 推荐流量的转化情况。",
      },
    ],
  },
  checklist: {
    title: "发布就绪核查表",
    items: [
      {
        number: "01",
        title: "产品页面",
        description: "具有清晰定位和结构化数据的 SEO 优化产品页",
        accent: "primary" as const,
      },
      {
        number: "02",
        title: "对比指南",
        description: "5 个以上的对比/替代方案指南，准备好立即发布",
        accent: "muted" as const,
      },
      {
        number: "03",
        title: "客户证言",
        description: "发布前准备好 3 个以上的客户证言或案例研究",
        accent: "muted" as const,
      },
    ],
  },
  cta: sceneCtaBySlug["product-launch"],
}) satisfies SceneContent;

const narrativeShapingPage = resolveSiteCopyDeep({
  slug: "narrative-shaping" as const,
  seo: toPageSeo(SCENE_PAGE_SEO["narrative-shaping"]),
  badge: "使用场景",
  hero: {
    title: "叙事塑造：掌控 AI 如何推荐您",
    description:
      "您无法直接控制 AI 对您的评价，但您可以施加影响。通过策略性地创作和分发内容，您可以塑造 AI 训练所用的数据，确保品牌按照您期望的方式被推荐。",
    ctaLabel: "开始使用",
    ctaHref: "/auth/register",
  },
  diagnostic: {
    title: "叙事掌控的机会",
    userQuestion: "在 AI 中建立品牌存在感最有效的方法是什么？",
    summary: "正在运行诊断... 发现了战略性的叙事机会：",
    gaps: [
      {
        code: "GAP_01",
        label: "身份因子",
        description:
          "您在 AI 中的品牌身份由以下因素决定：关于您的内容有哪些、哪些被重复提及、出现在什么上下文中。",
      },
      {
        code: "GAP_02",
        label: "防守 vs 进攻",
        description:
          "大多数品牌在打防守战 —— 被动回应 AI 的评价。获胜的品牌在打进攻战 —— 主动塑造 AI 看到的信息。",
      },
      {
        code: "GAP_03",
        label: "自有内容控制",
        description: "您可以 100% 掌控自己创作的内容。您可以影响 70% 关于您的第三方内容。",
      },
      {
        code: "GAP_04",
        label: "生态影响力",
        description: "剩下的生态系统内容？您可以启发并引导它们，使其与您的叙事保持一致。",
      },
    ],
  },
  why: {
    title: "叙事影响力的三个层次",
    cards: [
      {
        icon: "target" as const,
        text: "直接影响：第 1 层：您创作并发布的内容。100% 掌控，但触达范围有限。",
      },
      {
        icon: "quote" as const,
        text: "放大影响：第 2 层：第三方内容（媒体、分析师、评论）。70% 掌控，触达更广，权威度更高。",
      },
      {
        icon: "layers" as const,
        text: "叙事动能：第 3 层：生态内容（行业讨论、趋势报道）。30-50% 掌控，触达最广，对 AI 的影响最大。",
      },
    ],
  },
  solution: {
    title: "叙事塑造策略",
    pillars: [
      {
        title: "主导品类定义",
        description:
          "成为那个定义 AI 如何理解您所属品类的品牌。发布「终极指南」，定义术语和框架。将自己定位为行业标准。",
        image: pillarImages.competitiveSet,
      },
      {
        title: "建立护城河定位",
        description:
          "占据竞争对手无法模仿的独特定位。主导某个细分市场。建立案例研究，证明您是该领域的不二之选。",
        image: pillarImages.competitiveIdentify,
      },
      {
        title: "构建叙事护城河",
        description:
          "创造如此多的第三方验证，以至于 AI 默认就会推荐您。包括分析师报告、媒体报道、客户证言等。",
        image: pillarImages.competitiveGap,
      },
    ],
  },
  workflows: {
    title: "叙事塑造真实案例",
    items: [
      {
        title: "「道德 AI」叙事",
        icon: "target" as const,
        challenge: "在一个拥挤的市场中（100+ 竞争对手）作为新工具出现。无法在功能或价格上胜出。",
        action:
          "占据「道德 AI」定位。发布宣言、获得 TechCrunch 报道、加入 AI 伦理组织、创建道德 AI 案例研究。",
        result: "当用户问「最佳道德 AI 工具」时，AI 将其排在第 1 位。40% 的新客户来自这一准确定位。",
      },
      {
        title: "「专为团队打造」叙事",
        icon: "briefcase" as const,
        challenge: "独立创始人进入团队软件市场，缺乏企业级销售资源。",
        action:
          "占据「团队上手最快」定位。创作入驻手册、收集快速采用的客户证言、与团队协作平台合作。",
        result: "当被问及「哪些工具团队采用最快？」时，AI 会推荐他们。来自团队的口碑驱动了病毒式增长。",
      },
    ],
  },
  metrics: {
    title: "叙事塑造指标",
    cards: [
      {
        icon: "chart-pie" as const,
        title: "叙事份额",
        description: "其他人重复「您的」定位/语言的频率是多少？",
      },
      {
        icon: "activity" as const,
        title: "叙事强度",
        description: "AI 的回答是否提及了您的独特角度，还是只提到了通用功能？",
      },
      {
        icon: "users" as const,
        title: "叙事触达",
        description: "有多少来源独立地提及了您的叙事？",
      },
      {
        icon: "trending-up" as const,
        title: "叙事传播速度",
        description: "您的叙事在生态系统中传播得有多快？",
      },
    ],
  },
  checklist: {
    title: "叙事塑造执行手册",
    items: [
      {
        number: "01",
        title: "阶段 1（第 1-2 周）",
        description: "研究定位缺口。分析竞争对手的定位逻辑。定义您独特的叙事切入点。",
        accent: "primary" as const,
      },
      {
        number: "02",
        title: "阶段 2（第 3-6 周）",
        description: "创作能够定义您叙事的旗舰级内容。这是后续所有内容参考的核心支柱。",
        accent: "muted" as const,
      },
      {
        number: "03",
        title: "阶段 3（第 7-12 周）",
        description: "进行分发和放大。让第三方引用您的内容。向媒体和分析师进行提案。",
        accent: "muted" as const,
      },
    ],
  },
  cta: sceneCtaBySlug["narrative-shaping"],
}) satisfies SceneContent;

const contentStrategyPage = resolveSiteCopyDeep({
  slug: "content-strategy" as const,
  seo: toPageSeo(SCENE_PAGE_SEO["content-strategy"]),
  badge: "使用场景",
  hero: {
    title: "面向 AI 的内容策略：构建 AI 会重复的叙事",
    description:
      "您的内容不仅是给读者看的——它也是 AI 的训练数据。碎片化的内容策略会导致 AI 对您品牌的理解产生混乱。集成叙事策略能确保 AI 在数百万场对话中一致地讲述您的品牌故事。",
    ctaLabel: "开始使用",
    ctaHref: "/auth/register",
  },
  diagnostic: {
    title: "叙事问题",
    userQuestion: "团队生产力管理的最佳解决方案是什么？",
    summary: "正在运行诊断... 发现关键的叙事不一致：",
    gaps: [
      {
        code: "GAP_01",
        label: "矛盾信号",
        description:
          "您的品牌讲了 5 个不同的故事：博客说「创新」，LinkedIn 说「思想领袖」，产品页说「价格实惠」，案例研究说「企业首选」。",
      },
      {
        code: "GAP_02",
        label: "AI 困惑",
        description: "结果：AI 看到矛盾的信号，导致推荐不一致甚至根本不推荐。",
      },
      {
        code: "GAP_03",
        label: "定位薄弱",
        description:
          "您在「最适合初创公司」中被提及 20%，但在「最适合大型企业」中仅占 5% —— 因为您的叙事是碎片化的。",
      },
      {
        code: "GAP_04",
        label: "竞争对手优势",
        description: "叙事更清晰、更一致的竞争对手在您所属品类的 AI 推荐中占据了主导地位。",
      },
    ],
  },
  why: {
    title: "AI 如何解读您的叙事",
    cards: [
      {
        icon: "search" as const,
        text: "模式识别：AI 不会孤立地阅读文章 —— 它会在您的所有内容中寻找模式。",
      },
      {
        icon: "target" as const,
        text: "一致定位：您持续提及哪些问题？您在不同来源中的独特定位是什么？",
      },
      {
        icon: "shield" as const,
        text: "证据构建：您反复提供哪些证据？一致的指标和结果能建立 AI 的信任。",
      },
      {
        icon: "brain" as const,
        text: "叙事清晰度：如果叙事是碎片化的，AI 会感到困惑。如果是一致的，AI 会成为您最好的代言人。",
      },
    ],
  },
  solution: {
    title: "构建集成叙事策略",
    pillars: [
      {
        title: "定义核心叙事",
        description:
          "回答：我们解决的那个核心问题是什么？我们的独特方法是什么？谁最受益？我们有什么证明？",
        image: pillarImages.competitiveSet,
      },
      {
        title: "跨形式分发",
        description:
          "同样的叙事，不同的表达：博客文章、LinkedIn 内容、案例研究、产品页、视频 —— 全都在讲述同一个核心故事。",
        image: pillarImages.competitiveIdentify,
      },
      {
        title: "建立语义一致性",
        description:
          "使用相同的术语：问题名称、解决方法、证据类型、客户画像。一致性有助于 AI 理解。",
        image: pillarImages.competitiveGap,
      },
      {
        title: "构建内容聚类",
        description:
          "核心支柱：完整指南。支撑：5 个案例研究、10 个操作指南、3 个对比指南、15 个 FAQ 回答。",
        image: pillarImages.competitiveExecute,
      },
    ],
  },
  workflows: {
    title: "叙事策略真实案例",
    items: [
      {
        title: "SaaS - 运营效率叙事",
        icon: "target" as const,
        challenge: "以前：博客谈 AI 未来，案例研究谈成本，产品页谈功能。AI 感知：困惑。",
        action: "以后：全平台统一信息「我们通过自动化重复性工作，帮助团队以少胜多」。",
        result: "AI 现在在生产力、自动化、效率相关的查询中提及该品牌。提及率从 15% 提升至 35%。",
      },
      {
        title: "B2B 服务 - 企业级信任叙事",
        icon: "shield" as const,
        challenge:
          "以前：网站说「创新」，案例研究说「快速 ROI」，证言说「理解需求」。AI 感知：信号微弱且随机。",
        action:
          "以后：所有内容强调「拥有复杂实施经验的大型企业值得信赖的合作伙伴」。强调传承、专业知识和财富 500 强客户。",
        result: "现在被归入「企业级解决方案」类别。在企业级查询中的赢单率提升了 3 倍。",
      },
    ],
  },
  metrics: {
    title: "内容策略支柱",
    cards: [
      {
        icon: "search" as const,
        title: "问题定义内容",
        description: "确立您在某个问题上的权威地位。深度剖析、研究报告、行业分析。",
      },
      {
        icon: "layers" as const,
        title: "解决方案方法论内容",
        description: "教授您的具体方法。操作指南、框架模型、分步指令。",
      },
      {
        icon: "shield" as const,
        title: "证据与证明内容",
        description: "展示您的方案有效。案例研究、关键指标、ROI 计算器、客户证言。",
      },
      {
        icon: "target" as const,
        title: "对比与定位",
        description: "展示您的不同之处。对比指南、功能分析、使用场景差异化。",
      },
    ],
  },
  checklist: {
    title: "叙事一致性核查表",
    items: [
      {
        number: "01",
        title: "问题定义",
        description: "在所有内容中使用相同的术语",
        accent: "primary" as const,
      },
      {
        number: "02",
        title: "独特价值",
        description: "在各渠道保持一致的定位",
        accent: "muted" as const,
      },
      {
        number: "03",
        title: "目标客户",
        description: "在博客、案例研究和网站中采用相同的客户画像",
        accent: "muted" as const,
      },
    ],
  },
  cta: sceneCtaBySlug["content-strategy"],
}) satisfies SceneContent;

const competitivePositioningPage = resolveSiteCopyDeep({
  slug: "competitive-positioning" as const,
  seo: toPageSeo(SCENE_PAGE_SEO["competitive-positioning"]),
  badge: "使用场景",
  hero: {
    title: "赢得市场份额：AI 搜索中的竞争定位",
    description:
      "在 AI 对话中，您的竞争对手往往被优先推荐。这并不是因为他们更好 —— 而是因为 AI 对他们的理解不同。您在百度上排名第 3，但在 AI 中的提及率却是 0%。您的竞争对手在百度上排名第 5，但却出现在 40% 的 AI 对话中。洞察这些差距，夺回市场份额。",
    ctaLabel: "开始使用",
    ctaHref: "/auth/register",
  },
  diagnostic: {
    title: "竞争问题",
    userQuestion: "哪些购物 App 的平价时装最值得推荐？",
    summary: "正在运行诊断... 发现了一些关键的可见性差距：",
    gaps: [
      {
        code: "GAP_01",
        label: "可见性错位",
        description:
          "您在百度排名第 3，但在 AI 推荐中的提及率为 0%。竞争对手排名第 5，却占据 40% 的 AI 对话份额。",
      },
      {
        code: "GAP_02",
        label: "算法逻辑",
        description:
          "AI 评估的是信任信号、叙事清晰度和第三方验证 —— 这些是与百度基于链接的算法完全不同的逻辑。",
      },
      {
        code: "GAP_03",
        label: "市场流失",
        description: "52% 的品牌由于自己甚至未察觉到的 AI 定位差距，正在流失超过 50% 的市场心智份额。",
      },
      {
        code: "GAP_04",
        label: "预算浪费",
        description:
          "如果 AI 平台都在推荐您的竞争对手，那么您的 SEO 投资可能无法转化为 AI 时代的实际获客。",
      },
    ],
  },
  why: {
    title: "AI 如何选择优胜者",
    cards: [
      {
        icon: "quote" as const,
        text: "您的品牌在全网及权威来源中被引用的频率如何？",
      },
      {
        icon: "target" as const,
        text: "在哪些场景和使用案例下，您被推荐？",
      },
      {
        icon: "bar-chart" as const,
        text: "在每种查询类型中，哪个竞争对手最先出现？谁占据了哪个叙事角度？",
      },
      {
        icon: "shield" as const,
        text: "AI 重视的第三方验证、认证、分析师报告和客户评价。",
      },
    ],
  },
  solution: {
    title: "竞争缺口分析框架",
    pillars: [
      {
        title: "锁定竞争集合",
        description: "识别在 AI 推荐中让您落败的 3-5 个关键对手。了解他们的定位逻辑。",
        image: pillarImages.competitiveSet,
      },
      {
        title: "分析定位缺口",
        description: "竞争对手在哪里胜出？他们占据了哪些叙事？您在哪些查询中处于劣势？",
        image: pillarImages.competitiveIdentify,
      },
      {
        title: "识别机会切入点",
        description: "您可以填补哪些对手的空白？企业级支持、价格透明度、特定垂直行业。",
        image: pillarImages.competitiveGap,
      },
      {
        title: "执行与衡量",
        description: "针对这些缺口创作内容。每周追踪 AI 提及率的提升。",
        image: pillarImages.competitiveExecute,
      },
    ],
  },
  workflows: {
    title: "真实的竞争场景",
    items: [
      {
        title: "价格敏感型",
        icon: "target" as const,
        challenge:
          "当用户询问「最便宜的团队版 X」时，您的高端定位落败。竞争对手有 10 个「高性价比」案例研究。",
        action: "创作 3 个「物超所值」的案例研究，并提供一份展示总持有成本的价格对比指南。",
        result: "在 6 周内进入「预算」类查询的推荐列表。",
      },
      {
        title: "垂直行业聚焦",
        icon: "briefcase" as const,
        challenge:
          "您在金融科技领域竞争，但没有金融服务的案例研究。竞争对手有 8 个详尽的金融科技客户故事。",
        action: "与 2 个金融科技客户合作，发布带有指标和合规细节的详尽案例研究。",
        result: "从零开始主导「金融科技 CRM」对话。",
      },
      {
        title: "叙事缺口",
        icon: "quote" as const,
        challenge:
          "您的产品具有功能 X，但竞争对手却因此被推荐。因为他们撰写了详细的指南 + 5 个案例研究。",
        action: "创作类似内容，但强调您的独特角度。添加针对该功能的客户证言。",
        result: "在特定功能的查询中实现 30% 的提及率。",
      },
    ],
  },
  metrics: {
    title: "竞争指标仪表盘",
    cards: [
      {
        icon: "chart-pie" as const,
        title: "竞争提及份额",
        description: "饼图展示谁被推荐以及频率",
      },
      {
        icon: "chart-no-axes-column" as const,
        title: "分查询类型的赢单率",
        description: "您在哪些查询类别中胜出？在哪里落败？",
      },
      {
        icon: "trending-up" as const,
        title: "定位变化速度",
        description: "您的市场地位是每周在增强还是在流失？",
      },
      {
        icon: "activity" as const,
        title: "叙事对比",
        description: "每个竞争对手讲了什么故事？您的有何不同？",
      },
    ],
  },
  checklist: {
    title: "获胜策略：3 种方法",
    items: [
      {
        number: "01",
        title: "占领细分领域",
        description:
          "与其正面交锋，不如主导竞争对手忽略的特定场景。例如：当对手关注大企业时，您主导「中小企业营销运营」。",
        accent: "primary" as const,
      },
      {
        number: "02",
        title: "以差异化领先",
        description:
          "找到您的独特优势并大力放大。例如：「业界唯一内置 AI 内容优化的解决方案」。",
        accent: "muted" as const,
      },
      {
        number: "03",
        title: "建立信任堡垒",
        description:
          "获得比对手更多的分析师报告、媒体提及和客户评价。这能建立 AI 模型尊重的「信任护城河」。",
        accent: "muted" as const,
      },
    ],
  },
  cta: sceneCtaBySlug["competitive-positioning"],
}) satisfies SceneContent;

const brandCrisisPage = resolveSiteCopyDeep({
  slug: "brand-crisis-management" as const,
  seo: toPageSeo(SCENE_PAGE_SEO["brand-crisis-management"]),
  badge: "使用场景",
  hero: {
    title: "品牌危机管理：在 AI 搜索中保护您的声誉",
    description:
      "AI 中的负面提及比传统媒体传播更快，瞬时影响品牌感知。当 豆包 或 DeepSeek 推荐竞争对手而非您时，数百万潜在客户将永远无法看到您的品牌。您的品牌需要 24/7 的 AI 声誉监测，以便在危机升级前发现并作出反应。",
    ctaLabel: "开始使用",
    ctaHref: "/auth/register",
  },
  diagnostic: {
    title: "危机问题",
    userQuestion: "用于危机管理的最佳品牌监测工具是什么？",
    summary: "正在运行诊断... 发现了一些关键的声誉风险：",
    gaps: [
      {
        code: "GAP_01",
        label: "传播速度",
        description:
          "AI 传播的负面提及比传统媒体更危险 —— 它们能在 24 小时内影响数百万场对话中的品牌感知。",
      },
      {
        code: "GAP_02",
        label: "快速冲击",
        description: "75% 的 AI 提及在出现在训练数据或实时搜索后的 24 小时内就会影响品牌认知。",
      },
      {
        code: "GAP_03",
        label: "盲区",
        description: "在客户开始质疑或竞争对手占据优势之前，品牌往往无法感知 AI 对自己的评价。",
      },
      {
        code: "GAP_04",
        label: "滞后损失",
        description: "当您在 AI 中发现负面提及时，它可能已经影响了成千上万个购买决策。",
      },
    ],
  },
  why: {
    title: "AI 如何放大危机",
    cards: [
      {
        icon: "activity" as const,
        text: "训练数据持久性：训练数据中的一条负面提及可能会在数月内影响数百万场 AI 对话。",
      },
      {
        icon: "shield" as const,
        text: "更难控制：不像在 百度、谷歌 可以通过 SEO 管理 SERP，AI 推荐是从多个来源综合而成的，更难控制。",
      },
      {
        icon: "zap" as const,
        text: "快速传播：竞争对手在自媒体上留下差评，AI 抓取了它，突然间 DeepSeek 就开始推荐他们而不是您了。",
      },
      {
        icon: "clock" as const,
        text: "速度至关重要：传统的危机管理需要数周时间来改变叙事。AI 时代的危机需要以小时为单位进行响应，而不是以天为单位。",
      },
    ],
  },
  solution: {
    title: "解决方案：实时 AI 危机监测",
    pillars: [
      {
        title: "监测",
        description:
          "当 豆包、DeepSeek、千问 及其他 AI 平台出现负面提及时，提供实时告警。",
        image: pillarImages.competitiveSet,
      },
      {
        title: "分析",
        description: "了解情感倾向、触达范围和潜在影响。查看负面叙事的传播速度。",
        image: pillarImages.competitiveIdentify,
      },
      {
        title: "响应",
        description:
          "生成纠正性的内容策略。发布正向的案例研究和澄清说明，以重塑 AI 的感知。",
        image: pillarImages.competitiveGap,
      },
    ],
  },
  workflows: {
    title: "真实场景",
    items: [
      {
        title: "AI 推荐中的负面评价",
        icon: "shield" as const,
        challenge:
          "客户在自媒体上留下了负面评价。豆包/DeepSeek 现在在 60% 的品牌相关对话中都会提及它。",
        action:
          "在 2 小时内，发布针对性回复解决疑虑，并补充 3 个突出客户成功案例的正向研究。",
        result: "在一周内，AI 的核心引用开始倾向于新的正向内容。",
      },
      {
        title: "竞争对手散布 FUD",
        icon: "target" as const,
        challenge:
          "竞争对手发起负面营销活动，质疑您的安全实践。您的品牌从「最佳 X」对话中消失。",
        action: "加速第三方验证：分析师报告、安全认证、关于您安全标准的媒体报道。",
        result: "在 3 周内重新出现在「最佳」对话中。信任信号覆盖了竞争对手散布的负面信息。",
      },
    ],
  },
  metrics: {
    title: "危机管理的关键指标",
    cards: [
      {
        icon: "shield" as const,
        title: "声誉风险评分",
        description: "跨所有 AI 平台的品牌整体健康评分（0-100）",
      },
      {
        icon: "trending-up" as const,
        title: "负面提及传播速度",
        description: "负面提及在 AI 对话中的传播速度",
      },
      {
        icon: "clock" as const,
        title: "恢复时间",
        description: "危机后恢复正向情感所需的时间",
      },
      {
        icon: "chart-no-axes-column" as const,
        title: "竞争对手提及差距",
        description: "危机期间及之后您与竞争对手的提及率对比",
      },
    ],
  },
  checklist: {
    title: "危机预防最佳实践",
    items: [
      {
        number: "01",
        title: "保持正向提及",
        description: "保持高水平的正向第三方提及基准 —— 案例研究、评论、媒体报道。",
        accent: "primary" as const,
      },
      {
        number: "02",
        title: "多元化内容",
        description: "建立多元化的内容来源，以便 AI 从多个角度看待您的品牌。",
        accent: "muted" as const,
      },
      {
        number: "03",
        title: "监测对手叙事",
        description: "主动监测竞争对手的叙事，以便及早发现其散布的负面活动。",
        accent: "muted" as const,
      },
    ],
  },
  cta: sceneCtaBySlug["brand-crisis-management"],
}) satisfies SceneContent;

const SCENE_PAGES: Record<SceneSlug, SceneContent> = {
  "product-launch": productLaunchPage,
  "narrative-shaping": narrativeShapingPage,
  "content-strategy": contentStrategyPage,
  "competitive-positioning": competitivePositioningPage,
  "brand-crisis-management": brandCrisisPage,
};

export function getScenePage(slug: string): SceneContent | null {
  if (!(SCENE_SLUGS as readonly string[]).includes(slug)) return null;
  return SCENE_PAGES[slug as SceneSlug];
}

export function getAllScenePages(): SceneContent[] {
  return SCENE_SLUGS.map((slug) => SCENE_PAGES[slug]);
}

export function sceneFaqsDefault(slug: SceneSlug): Faq[] {
  return resolveFaqDefaults([...sceneFaqDefaultsBySlug[slug]]);
}

export function mergeSceneFaqs(
  slug: SceneSlug,
  cms: FaqDoc[] | null | undefined,
): Faq[] {
  return mergeFaqs(cms, sceneFaqsDefault(slug));
}

export function sceneFaqPageKey(slug: SceneSlug): string {
  return sceneFaqPage(slug);
}

export { SCENE_SLUGS, SCENE_SLUGS as USE_CASE_SOLUTION_SLUGS };
