import { mergeFaqs, resolveFaqDefaults, type Faq } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import { teamSolutionFaqDefaultsBySlug } from "@shared/faq/defaults";
import {
  TEAM_SOLUTION_SLUGS,
  teamSolutionFaqPage,
  type TeamSolutionSlug,
} from "@shared/faq/pages";
import { SOLUTION_TEAM_SEO } from "@shared/seo/defaults/solution";
import { toPageSeo } from "@/lib/seo";
import { resolveSiteCopyDeep } from "@/lib/site";
import { createSolutionCta } from "@/lib/solution/cta";
import { SOLUTION_FEATURE_IMAGES } from "@/lib/solution/feature";
import type { TeamSolutionContent } from "@/lib/solution/types";
import { appLinks } from "@/lib/app-links";

const featureImages = SOLUTION_FEATURE_IMAGES;

const agenciesPage = resolveSiteCopyDeep({
  slug: "agencies" as const,
  seo: toPageSeo(SOLUTION_TEAM_SEO.agencies),
  badge: "面向团队",
  hero: {
    title: "代理商：大规模管理多个客户的 AI 可见性",
    description:
      "您正在管理 20 多个客户的 SEO。现在客户问：“我们在 豆包 里有推荐吗？” 您没有答案。您需要一个工具，让您的团队能在一个地方监测并优化所有客户的 AI 可见性，并提供能打动客户的专业报告，而无需自定义仪表盘。",
    ctaLabel: "开始使用",
    ctaHref: appLinks.register,
  },
  why: {
    title: "为何 GEO 现在至关重要",
    cards: [
      {
        number: "01",
        title: "掌握 GEO = AI 时代的专家顾问",
        bodyHtml:
          '掌握 GEO 的代理商将成为<span class="font-semibold">「AI 时代的专家顾问」</span>。客户越来越多地询问「GEO 如何融入我们的 SEO？」没有答案就意味着失去订单。',
      },
      {
        number: "02",
        title: "竞争护城河",
        bodyHtml:
          '如果您的竞争对手尚未采用 GEO 工具，您可以通过提供统一的「SEO + GEO」监测来<span class="font-semibold">赢得新客户</span>。',
      },
      {
        number: "03",
        title: "新的服务线",
        bodyHtml:
          'GEO 创造了新的服务增长点：<span class="font-semibold">「AI 可见性审计」、「豆包优化服务」、「多模型监测」</span>。这些服务的定价可以高于传统 SEO。',
      },
      {
        number: "04",
        title: "平台化规模",
        bodyHtml:
          '使用平台（而非手动监测）大规模管理 GEO，让代理商能在<span class="font-semibold">不增加成比例成本的情况下交付 GEO 服务</span>。',
      },
    ],
  },
  challenges: {
    title: "代理商面临的挑战",
    cards: [
      {
        title: "单客经济模型失效",
        description:
          "现在每个客户都想要 GEO。但 GEO 工具按站点收费非常昂贵，当您有 20-100 个客户时，经济模型就难以为继。",
        icon: "coins" as const,
      },
      {
        title: "工作流复杂性",
        description:
          "您的 SEO 团队负责优化，策略团队检查 AI 影响，客户成功团队负责汇报。GEO 变成了三个独立的流程。",
        icon: "git-branch" as const,
      },
      {
        title: "流失风险",
        description:
          "如果客户看不到「AI 可见性」方面的进展，他们会认为您没有跟上他们不断变化的需求，转而选择那些能提供该服务的代理商。",
        icon: "trending-down" as const,
      },
      {
        title: "招聘难题",
        description: "您无法雇佣 5 个新的 GEO 专家。您需要通过工具让现有的 SEO 团队具备「GEO 能力」。",
        icon: "user-x" as const,
      },
    ],
  },
  solution: {
    title: "我们的代理商解决方案",
    description:
      "一个以代理商为中心的平台，具有白标仪表盘、不限客户数量、团队权限控制和批量报告功能。",
    pillars: [
      { title: "白标仪表盘", description: "白标仪表盘，让您可以以自己的品牌提供服务", icon: "layout-dashboard" as const },
      { title: "不限客户数量", description: "随客户组合增长而扩展，无需按站点线性加价", icon: "users" as const },
      { title: "团队权限控制", description: "分析师只看分配客户，策略师掌握完整组合", icon: "shield" as const },
      { title: "批量报告", description: "为数十个客户一键生成月度 AI 可见性报告", icon: "files" as const },
      { title: "API 访问", description: "对接自有 BI、CRM 或客户门户的自定义集成", icon: "code" as const },
    ],
  },
  features: {
    title: "核心功能",
    cards: [
      {
        title: "多客户仪表盘",
        description: "在一个视图中监测 50 多个客户的 AI 可见性趋势。快速发现哪些客户需要关注。",
        image: featureImages.aiMonitor,
        area: "card1" as const,
      },
      {
        title: "白标报告",
        description: "为您的客户生成品牌月度报告。展示排名、AI 引用、建议 —— 全部带有您的 Logo。",
        image: featureImages.brandInfluence,
        area: "card2" as const,
      },
      {
        title: "批量优化",
        description:
          "识别您客户组合中的模式：「您 30% 的客户缺乏 FAQ Schema。以下是批量修复的方法。」",
        image: featureImages.competitiveWinLoss,
        area: "card3" as const,
      },
      {
        title: "团队权限与工作流",
        description: "将初级团队成员分配给特定客户。他们只能看到自己的账户。审批流转给高级策略师。",
        image: featureImages.narrativeIntelligence,
        area: "card4" as const,
      },
      {
        title: "代理商洞察",
        description:
          "将您的客户组合与行业基准进行对比。「您客户的平均 AI 提及率为 22%，行业平均水平为 18%。您正处于领先地位。」",
        image: featureImages.customAttribution,
        area: "card5" as const,
      },
    ],
  },
  workflows: {
    title: "真实工作流",
    items: [
      {
        title: "入驻新客户",
        accent: "primary" as const,
        steps: [
          { text: "潜在客户会议：客户问「你们针对 AI 搜索做了什么？」" },
          {
            text: "您的团队打开白标仪表盘，展示「这就是我们将如何每月在 ChatGPT、Perplexity 和 Gemini 中追踪您的品牌」。",
            highlight: true,
          },
          { text: "客户看到专业的报告，理解了价值，签署了「每月 500 美元以上的 AI 监测服务」合同。" },
          { text: "您现在无需高薪聘请专员即可提供 GEO 服务。" },
        ],
      },
      {
        title: "资产组合优化活动",
        accent: "orange" as const,
        steps: [
          {
            text: "第二季度启动：您分析了 40 个客户的资产组合。发现其中 15 个客户虽然搜索排名很好，但 AI 引用率却很低。",
          },
          {
            text: "您的内容团队创建了「GEO 优化包」：审计 + 3 个页面优化 + 培训。将其作为增值服务向这 15 个客户中的 10 个进行销售。",
            highlight: true,
          },
          { text: "结果：基于数据洞察，成功售出了 7.5 万美元的额外服务。" },
          { text: "您的工具成本：得益于平台，仅投入了约 20 小时的工作时间。" },
        ],
      },
    ],
  },
  cta: createSolutionCta("加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。"),
}) satisfies TeamSolutionContent;

const enterprisePage = resolveSiteCopyDeep({
  slug: "enterprise" as const,
  seo: toPageSeo(SOLUTION_TEAM_SEO.enterprise),
  badge: "面向团队",
  hero: {
    title: "企业级：提升 AI 品牌影响力和信任度，而不止于可见性",
    description:
      "对于大型企业来说，被 AI 提及是不够的。重要的是您如何被理解。影响力是指当 1,000 个 豆包 用户询问您的品类时，有 700 个选择了您。了解 AI 模型如何解析并推荐您的品牌，并策略性地塑造这种感知，是企业在 AI 优先时代获胜的关键。",
    ctaLabel: "开始使用",
    ctaHref: appLinks.register,
  },
  why: {
    title: "为何 GEO 现在至关重要",
    cards: [
      {
        number: "01",
        title: "新的 KPI",
        bodyHtml:
          '对于企业而言，GEO 不仅仅是一种新战术 —— <span class="font-semibold">它是一个新的 KPI</span>。核心问题不再是“我们的排名如何？”，而是“市场如何通过 AI 感知我们？”',
      },
      {
        number: "02",
        title: "全球规模",
        bodyHtml:
          '如果您在 <span class="font-semibold">10 多个市场</span>运营，您需要追踪每个地区的 AI 影响力。某些地区可能存在正向偏差，而另一些地区可能是负向的。',
      },
      {
        number: "03",
        title: "实质性差异化",
        bodyHtml:
          '在竞争极其激烈的品类（金融服务、医疗保健、科技）中，被 AI 推荐是一个<span class="font-semibold">实质性的差异化优势</span>。',
      },
      {
        number: "04",
        title: "收入影响",
        bodyHtml:
          '企业需要向董事会和投资者解释 AI 搜索如何影响<span class="font-semibold">品牌感知和未来收入</span>。',
      },
    ],
  },
  challenges: {
    title: "企业面临的挑战",
    cards: [
      {
        title: "对齐问题",
        description:
          "庞大的 SEO 和营销团队难以在“什么对 AI 可见性重要”上达成一致。传统指标无法捕捉 AI 中的品牌影响力。",
        icon: "coins" as const,
      },
      {
        title: "训练数据风险",
        description:
          "如果主流 AI 模型使用了关于您公司的陈旧或负面数据进行训练怎么办？您需要预警和补救能力。",
        icon: "git-branch" as const,
      },
      {
        title: "团队孤岛",
        description:
          "您的 SEO、公关、产品和分析团队没有统一的 GEO 策略。各团队都在孤立地追求自己的目标。",
        icon: "trending-down" as const,
      },
      {
        title: "高管汇报缺口",
        description:
          "首席营销官 (CMO) 和品牌高级副总裁 (SVP) 希望看到 AI 存在感与业务成果之间更清晰的影响关联，而这目前是缺失的。",
        icon: "user-x" as const,
      },
    ],
  },
  solution: {
    title: "我们的企业级解决方案",
    description:
      "一个“战略品牌影响力平台”，而不止是一个工具。为 SEO、公关、产品反馈和客户数据提供统一的指挥中心。",
    pillars: [
      {
        title: "统一指挥中心",
        description: "整合 SEO、公关、产品反馈和客户数据",
        icon: "layout-dashboard" as const,
      },
      {
        title: "高管仪表盘",
        description: "月度“品牌影响力”报告，将 AI 可见性与业务成果挂钩",
        icon: "users" as const,
      },
      {
        title: "包含咨询服务",
        description: "我们的团队与企业合作，制定 12 个月的“AI 品牌策略”路线图",
        icon: "shield" as const,
      },
      {
        title: "API + 定制化集成",
        description: "连接到 CRM、销售数据和品牌追踪调查",
        icon: "code" as const,
      },
    ],
  },
  features: {
    title: "核心功能",
    cards: [
      {
        title: "全球 AI 监测",
        description:
          "在 50 多个国家及所有主流 AI 模型（ChatGPT、Perplexity、Gemini、Claude 等）中追踪品牌情感和定位。",
        image: featureImages.aiMonitor,
        area: "card1" as const,
      },
      {
        title: "品牌影响力评分",
        description:
          "高管易于理解的综合指标（提及频率 + 情感倾向 + 竞争地位 + 销售意向相关性）。",
        image: featureImages.brandInfluence,
        area: "card2" as const,
      },
      {
        title: "竞争赢单/损单分析",
        description: "量化在所有品类和地区中，您的品牌与前 5 名竞争对手相比被推荐的频率。",
        image: featureImages.competitiveWinLoss,
        area: "card3" as const,
      },
      {
        title: "叙事智能",
        description:
          "追踪关于您品牌的哪些叙事正在被 AI 放大（可信度信号、思想领导力、产品质量）。识别其中的缺口。",
        image: featureImages.narrativeIntelligence,
        area: "card4" as const,
      },
      {
        title: "定制化归因",
        description:
          "将 AI 提及量与下游业务指标（网站流量、潜客生成、销售额、NPS）联系起来。展示“AI 影响力”投资的 ROI。",
        image: featureImages.customAttribution,
        area: "card5" as const,
      },
    ],
  },
  workflows: {
    title: "真实工作流",
    items: [
      {
        title: "战略规划",
        accent: "primary" as const,
        steps: [
          {
            text: "首席营销官 (CMO) 第一季度规划发起请求：“我们需要了解 AI 将如何改变我们在 2026 年的市场定位。”",
          },
          {
            text: "平台提供：分地区的 AI 感知详细分析、竞争对手推荐逻辑、关键叙事缺口。例如：“在 EMEA 地区，竞争对手 A 的被推荐次数是我们的 2 倍。主要原因：他们拥有 3 倍于我们的第三方验证内容。”",
            highlight: true,
          },
          {
            text: "战略决策：投资于“受信任的顾问”类内容（行业奖项、分析师认可、客户证言），以提升在 EMEA 地区的 AI 感知度。",
          },
          {
            text: "衡量：按季度追踪 AI 影响力评分。ROI：在 EMEA 地区实施 6 个月后，品牌考虑度提升了 200 个基点。",
          },
        ],
      },
      {
        title: "危机恢复",
        accent: "orange" as const,
        steps: [
          {
            text: "突发新闻：竞争对手发起负面营销活动，或者出现了一篇关于您公司的负面报道。",
            highlight: true,
          },
          {
            text: "实时监测标记出 ChatGPT 的情感基调开始向负面转变（基于其训练来源）。",
          },
          {
            text: "您的企业团队立即行动：公关部撰写回应，产品团队突出展示客户成功案例，合作伙伴团队放大第三方背书。",
          },
          {
            text: "在 2 周内，AI 情感倾向恢复。更早的干预 + 统一的策略防止了对品牌感知的长期损害。",
          },
        ],
      },
    ],
  },
  cta: createSolutionCta("加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。"),
}) satisfies TeamSolutionContent;

const prBrandPage = resolveSiteCopyDeep({
  slug: "pr-brand-teams" as const,
  seo: toPageSeo(SOLUTION_TEAM_SEO["pr-brand-teams"]),
  badge: "面向团队",
  hero: {
    title: "公关与品牌团队：塑造关于品牌的 AI 对话",
    description:
      "您品牌的声誉现在存在于 AI 的回答中。如果有 100,000 个 豆包 用户问“某品牌是否可靠？”而 AI 推荐了竞争对手，那么在对话开始前您就已经输了。公关和品牌团队需要知道 AI 在说什么 —— 以及如何塑造这一叙事。",
    ctaLabel: "开始使用",
    ctaHref: appLinks.register,
  },
  why: {
    title: "为何 GEO 现在至关重要",
    cards: [
      {
        number: "01",
        title: "赢得 AI 推荐，而不止是媒体报道",
        bodyHtml:
          '传统公关侧重于<span class="font-semibold">“赢得媒体”</span> —— 让记者报道您。GEO 增加了新维度：<span class="font-semibold">“赢得 AI”</span>（被 AI 模型推荐）。',
      },
      {
        number: "02",
        title: "规模化影响力",
        bodyHtml:
          '当 AI 模型说<span class="font-semibold">“大多数人使用 [竞争对手]”</span>时，它会影响<span class="font-semibold">潜在数百万场对话</span>中的品牌认知。',
      },
      {
        number: "03",
        title: "品牌监测的进化",
        bodyHtml:
          '品牌监测以前是<span class="font-semibold">“人们在搜我们吗？”</span>。现在是<span class="font-semibold">“当人们询问该品类时，AI 模型是否推荐我们？”</span>',
      },
      {
        number: "04",
        title: "危机的复杂性",
        bodyHtml:
          '危机管理变得更难：<span class="font-semibold">AI 中的负面训练数据可能会持续数月</span>，除非您主动塑造叙事。',
      },
    ],
  },
  challenges: {
    title: "公关与品牌团队面临的挑战",
    cards: [
      {
        title: "AI 错误陈述",
        description:
          "AI 模型基于陈旧或负面数据进行训练。自媒体上的一个负面帖子可能会在数月内误导豆包对您品牌的理解。",
        icon: "coins" as const,
      },
      {
        title: "缺乏统一监测",
        description:
          "“豆包怎么评价我们？”以前只是随口一问，现在对业务至关重要。但目前缺乏统一的方法来监测 AI 中的品牌情感。",
        icon: "git-branch" as const,
      },
      {
        title: "被动而非主动",
        description:
          "公关团队对媒体报道做出反应，但很少能影响 AI 模型看到的内容。当危机爆发时，它往往已经固化在 AI 的训练数据中了。",
        icon: "trending-down" as const,
      },
      {
        title: "错失机会",
        description:
          "AI 可能会在“最佳产品”对话中推荐您的品牌，但前提是您的内容结构符合模型的偏好。大多数品牌并不了解这一点。",
        icon: "user-x" as const,
      },
    ],
  },
  solution: {
    title: "我们的公关与品牌团队解决方案",
    description: "一个监测 + 影响力平台，跨 AI 平台追踪品牌提及、情感倾向和竞争定位。",
    pillars: [
      {
        title: "多平台监测",
        description: "在 豆包、DeepSeek、通义千问、腾讯元宝、Kimi、文心一言中追踪品牌提及、情感和竞争定位",
        icon: "layout-dashboard" as const,
      },
      {
        title: "叙事建议",
        description: "获得具体的内容或公关建议以塑造品牌叙事",
        icon: "users" as const,
      },
      {
        title: "可行动的洞察",
        description:
          "例如：“豆包在 40% 的对话中推荐 [竞争对手 A]。请以 AI 模型偏好的格式发布详尽的案例研究。”",
        icon: "shield" as const,
      },
      {
        title: "清晰传达，而非操纵",
        description: "我们不是在操纵 AI；我们是在帮助您的品牌更清晰地沟通，以便 AI 模型能够准确地呈现它",
        icon: "files" as const,
      },
      {
        title: "实时告警",
        description: "当 AI 情感基调发生转变或竞争对手在 AI 对话中占据上风时，获取通知",
        icon: "code" as const,
      },
    ],
  },
  features: {
    title: "核心功能",
    cards: [
      {
        title: "品牌情感仪表盘",
        description: "跨平台查看 AI 对您品牌的评价（正向、中性、负向）。按平台和话题细分。",
        image: featureImages.aiMonitor,
        area: "card1" as const,
      },
      {
        title: "竞争定位",
        description: "追踪您相对于 3-5 个关键竞争对手的提及情况。如果竞争对手被推荐的频率高出 2 倍，系统将发出提醒。",
        image: featureImages.brandInfluence,
        area: "card2" as const,
      },
      {
        title: "叙事缺口分析",
        description: "我们的 AI 爬取当前的 AI 回答并识别：竞争对手宣称了什么？您有哪些主张尚未提及？",
        image: featureImages.competitiveWinLoss,
        area: "card3" as const,
      },
      {
        title: "危机监测",
        description: "如果负面报道开始发酵，提供实时告警。查看它已经如何影响了豆包的情感基调。",
        image: featureImages.narrativeIntelligence,
        area: "card4" as const,
      },
      {
        title: "针对 AI 的内容策略",
        description: "建议特定内容（博客、案例研究、FAQ），帮助 AI 模型更好地理解您的品牌。",
        image: featureImages.customAttribution,
        area: "card5" as const,
      },
    ],
  },
  workflows: {
    title: "真实工作流",
    items: [
      {
        title: "主动塑造叙事",
        accent: "primary" as const,
        steps: [
          {
            text: "第一季度规划会议：品牌团队运行报告，显示 DeepSeek 在“非营利组织 CRM”对话中提及他们的比例仅为 15%，而竞争对手为 60%。",
          },
          {
            text: "分析：该竞争对手有 5 个详尽的案例研究和一个关于非营利组织应用场景的 FAQ。而您的品牌只有一个通用的案例研究。",
            highlight: true,
          },
          {
            text: "公关团队行动：创建 3 个针对非营利组织的案例研究（严格按照 AI 模型偏好的格式：问题、解决方案、结果、指标）。按月发布。",
          },
          {
            text: "6 周后：DeepSeek 中的提及率攀升至 35%。不需要公关公司 —— 只需要针对 AI 理解而构建的内容。",
          },
        ],
      },
      {
        title: "危机与恢复",
        accent: "orange" as const,
        steps: [
          { text: "科技媒体出现了一篇关于您品牌数据隐私实践的负面文章。" },
          { 
            text: "在 24 小时内，您的监测仪表盘显示豆包的情感基调已转向负面。",
            highlight: true,
          },
          {
            text: "公关团队迅速行动：发布一篇详尽的回应文章澄清隐私实践，并附带链接到官方文档的透明政策。",
          },
          { text: "在 2 周内，豆包的情感倾向恢复。早期干预防止了该叙事在训练数据中钙化。" },
        ],
      },
    ],
  },
  cta: createSolutionCta("加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。"),
}) satisfies TeamSolutionContent;

const smbGeoPage = resolveSiteCopyDeep({
  slug: "smb-geo-teams" as const,
  seo: toPageSeo(SOLUTION_TEAM_SEO["smb-geo-teams"]),
  badge: "竞争情报",
  hero: {
    title: "中小企业 GEO 团队：提升 AI 可见性并构建品牌信任",
    description:
      "如今 AI 搜索的增长速度已超过传统搜索引擎。您也需要赢得 AI 可见性——但没有时间成为 GEO 专家。我们的工具削减复杂性，让您专注于快速见效。",
    ctaLabel: "开始使用",
    ctaHref: appLinks.register,
  },
  why: {
    title: "为何 GEO 现在至关重要",
    cards: [
      {
        number: "01",
        title: "首批可见增长",
        bodyHtml:
          'AICPB 披露截止2026年5月豆包的月活用户数已达 <span class="font-semibold">3.3亿。</span>更多用户使用 AI 进行搜索 = 更多品牌需要 AI 可见性。',
      },
      {
        number: "02",
        title: "40-60% AI 提及率",
        bodyHtml:
          '如果你处于细分领域（SaaS 工具、B2B 服务、本地服务），你可以成为<span class="font-semibold">你所在类别中首批针对 AI 进行优化</span>的企业之一。',
      },
      {
        number: "03",
        title: "流量乘数",
        bodyHtml:
          '为 AI 优化的内容通常<span class="font-semibold">在搜索引擎上也排名更好</span>（结构更清晰、标题更好）。这不是额外负担，而是倍增器。',
      },
      {
        number: "04",
        title: "竞争差距",
        bodyHtml:
          '<span class="font-semibold">许多中小企业竞争对手还没有考虑 AI。</span>如果你考虑了，你就赢了。',
      },
    ],
  },
  challenges: {
    title: "中小企业 GEO 团队面临的挑战",
    cards: [
      {
        title: "首批可见增长",
        description:
          "3-4 周内看到结果，长尾/垂直关键词见效更快",
        icon: "coins" as const,
      },
      {
        title: "40-60% AI 提及率",
        description:
          "3-6 个月内的典型目标（从 10-30% 起步）",
        icon: "git-branch" as const,
      },
      {
        title: "流量乘数",
        description:
          "SEO + GEO 结合产生的协同效应带来的额外推荐流量",
        icon: "user-x" as const,
      },
      {
        title: "自助式优化",
        description:
          "实时编辑建议：“添加 FAQ 块”、“让标题更清晰”、“扩展此段内容”",
        icon: "trending-down" as const,
      },
    ],
  },
  solution: {
    title: "我们的中小企业 GEO 团队解决方案",
    description:
      "简单、有明确指引的工具，准确告诉您该做什么，而不是提供 47 个选项。",
    pillars: [
      {
        title: "快速见效思维",
        description:
          "3-4 周内看到结果，长尾/垂直关键词见效更快",
        icon: "layout-dashboard" as const,
      },
      {
        title: "40-60% AI 提及率",
        description: "3-6 个月内的典型目标（从 10-30% 起步）",
        icon: "users" as const,
      },
      {
        title: "流量乘数",
        description: "SEO + GEO 结合产生的协同效应带来的额外推荐流量",
        icon: "files" as const,
      },
      {
        title: "自助式优化",
        description: "实时编辑建议：“添加 FAQ 块”、“让标题更清晰”、“扩展此段内容”",
        icon: "shield" as const,
      },
    ],
  },
  features: {
    title: "核心功能",
    cards: [
      {
        title: "一键 AI 就绪评分",
        description:
          "输入 URL，即可获得 1–100 即时评分及 3 条具体修复建议，告别分析瘫痪。",
        image: featureImages.aiMonitor,
        area: "card1" as const,
      },
      {
        title: "简洁监测仪表盘",
        description:
          "查看核心 10–20 个关键词的 AI 回答中是否提及您。仅此而已，没有 47 项指标。",
        image: featureImages.brandInfluence,
        area: "card2" as const,
      },
      {
        title: "2 分钟内容简报",
        description: "选择话题，获得一页简报，说明「写什么」以及「为何对 AI 重要」。",
        image: featureImages.competitiveWinLoss,
        area: "card3" as const,
      },
      {
        title: "自助式优化",
        description: "实时编辑建议：“添加 FAQ 块”、“让标题更清晰”、“扩展此段内容”。",
        image: featureImages.narrativeIntelligence,
        area: "card4" as const,
      },
      {
        title: "给老板的月度报告",
        description: "“我们现在在核心关键词的 AI 回答中提及率为 35%（高于 1 月份的 12%）。”",
        image: featureImages.customAttribution,
        area: "card5" as const,
      },
    ],
  },
  workflows: {
    title: "真实工作流",
    items: [
      {
        title: "快速见效（每周 1–2 小时）",
        accent: "primary" as const,
        steps: [
          {
            text: "周一：对 5 个头部页面运行快速审计。工具显示「3 个对 AI 友好，2 个需要修复。」",
          },
          {
            text: "周三：团队花 90 分钟为 2 个弱项页面添加 FAQ 板块并重组标题结构。",
            highlight: true,
          },
          { text: "周五：部署更改。" },
          {
            text: "结果：2 周后 AI 提及率上升。2 周内每周只需 2 小时，ROI 可衡量。",
          },
        ],
      },
      {
        title: "中小企业增长打法",
        accent: "orange" as const,
        steps: [
          {
            text: "第一季度规划：营销负责人决定“我们应该在所属品类中占据‘适合中小企业的最佳 X’这个话题”。",
          },
          {
            text: "我们的工具生成简报：4,000 次搜索量，100 个 豆包提示词，竞争对手内容深度较低。机会评分：8/10。",
            highlight: true,
          },
          { text: "团队使用我们的模板创建了一份对比指南。2 月发布。" },
          {
            text: "4 月：百度搜索排名第 3。在 10 个测试的 AI 回答中被提及 5 次。2 个月内生成了 200 个高质量潜在客户。",
          },
        ],
      },
    ],
  },
  cta: createSolutionCta("加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。"),
}) satisfies TeamSolutionContent;

const seoSpecialistsPage = resolveSiteCopyDeep({
  slug: "seo-specialists" as const,
  seo: toPageSeo(SOLUTION_TEAM_SEO["seo-specialists"]),
  badge: "面向团队",
  hero: {
    title: "SEO 专家：专为价格敏感型专业人士打造的实惠 GEO 工具",
    description:
      "您已经围绕 SEO 专长建立了业务。现在客户问：“AI 搜索该怎么办？”您想增加 GEO 服务，但不想让工具成本每月增加上千元。我们为追求强大功能且价格合理的 SEO 专家打造了 GEO 工具。",
    ctaLabel: "开始使用",
    ctaHref: appLinks.register,
  },
  why: {
    title: "为何 GEO 现在至关重要",
    cards: [
      {
        number: "01",
        title: "AI 时代专家顾问",
        bodyHtml:
          '学习 GEO 的 SEO 专家将成为<span class="font-semibold">“AI 就绪”顾问</span>。这在销售谈单中是一个<span class="font-semibold">竞争优势</span>。',
      },
      {
        number: "02",
        title: "更高的利润率",
        bodyHtml:
          'GEO 服务的<span class="font-semibold">利润率更高</span>：您可以针对一次“AI 可见性审计”收取 <span class="font-semibold">500-2,000 元</span> 的费用（费率高于传统 SEO 审计）。',
      },
      {
        number: "03",
        title: "客户留存",
        bodyHtml:
          '如果客户的核心问题是<span class="font-semibold">“我该如何进入豆包的回答？”</span>而您能回答，<span class="font-semibold">他们就会留下来。</span>',
      },
      {
        number: "04",
        title: "市场时机",
        bodyHtml:
          '大多数 SEO 专家还没弄清楚这一点。<span class="font-semibold">6-12 个月的认知领先优势 = 6-12 个月的高客单价期。</span>',
      },
    ],
  },
  challenges: {
    title: "SEO 专家面临的挑战",
    cards: [
      {
        title: "工具栈已经很贵了",
        description: "SEO 自由职业者通常使用 Semrush、Ahrefs 等工具。每月的工具总支出已达 800-1,200 美元。",
        icon: "coins" as const,
      },
      {
        title: "单客经济模型不成立",
        description:
          "在每个客户合作中再增加一个 1,500 美元/月以上的工具是不现实的。客户期望 GEO 服务，但您负担不起企业级工具。",
        icon: "git-branch" as const,
      },
      {
        title: "担心流失客户",
        description: "“如果我回答不了客户关于 AI 搜索的问题，我会失去他们吗？”这种压力是真实存在的。",
        icon: "trending-down" as const,
      },
      {
        title: "功能过载",
        description:
          "您不需要所有的企业级功能。您需要核心功能：“客户的网站在 AI 中可见吗？缺了什么？我该如何修复？”",
        icon: "user-x" as const,
      },
    ],
  },
  solution: {
    title: "我们的 SEO 专家解决方案",
    description: "一个专为管理自己客户的专业人士打造的“自由职业者优先”平台。无需复杂的大团队工作流。",
    pillars: [
      {
        title: "实惠的价格",
        description: "每月 199-399 美元即可覆盖 5-20 个客户的所有核心 GEO 监测和优化指导",
        icon: "layout-dashboard" as const,
      },
      {
        title: "简单的 UI",
        description: "没有 47 个标签页的复杂仪表盘。每个客户一个仪表盘。简单、清晰、可行动。",
        icon: "users" as const,
      },
      {
        title: "白标选项",
        description: "如果需要，可以进行白标处理 —— 让客户觉得这是您自己开发的工具",
        icon: "files" as const,
      },
      {
        title: "客户就绪的报告",
        description: "专业的报告，外观精美，并用客户易懂的语言解释 AI 可见性",
        icon: "code" as const,
      },
    ],
  },
  features: {
    title: "核心功能",
    cards: [
      {
        title: "一键客户审计",
        description: "输入客户的 URL（或导入前 10 个页面）。获得“AI 就绪评分” + 5 个具体的修复方案。",
        image: featureImages.aiMonitor,
        area: "card1" as const,
      },
      {
        title: "月度监测仪表盘",
        description: "追踪客户是否出现在其核心关键词的 AI 回答中。提供简单的“是/否”判定 + 趋势线。",
        image: featureImages.brandInfluence,
        area: "card2" as const,
      },
      {
        title: "模板化建议",
        description: "“基于此审计，这里有 3 个行动项。点击为您的客户生成单页简报。”",
        image: featureImages.competitiveWinLoss,
        area: "card3" as const,
      },
      {
        title: "白标报告",
        description: "所有报告/仪表盘均可使用您的品牌标识。客户会认为这是您开发的，从而让您可以收取更高费用。",
        image: featureImages.narrativeIntelligence,
        area: "card4" as const,
      },
      {
        title: "Slack 提醒",
        description: "当客户的 AI 可见性发生显著变化时获取通知（非常适合主动与客户沟通）。",
        image: featureImages.customAttribution,
        area: "card5" as const,
      },
    ],
  },
  workflows: {
    title: "真实工作流",
    items: [
      {
        title: "向现有客户推销增值服务",
        accent: "primary" as const,
        steps: [
          { text: "您正在为一家本地 SaaS 公司管理 SEO。他们排名还可以，但问到“AI 方面表现如何？”" },
          {
            text: "您使用我们的工具运行一次免费审计（15 分钟）。向他们展示 AI 就绪评分和 3 个缺口。",
            highlight: true,
          },
          { text: "客户很感兴趣。您提议一个“500 元的 AI 可见性审计 + 优化计划”（4 周，20,000 元）。" },
          { text: "您总共花费 6 小时。收费 20,000 元。效率是传统审计工作的 5 倍。" },
        ],
      },
      {
        title: "将 GEO 作为按月代运营服务",
        accent: "orange" as const,
        steps: [
          { text: "您有 10 个按月付费的客户。在服务中增加“AI 可见性监测”项（每个客户 500 元/月）。" },
          { text: "10 个客户 x 500 元 = 增加 5,000 元的月经常性收入 (MRR)。", highlight: true },
          { text: "您的工具成本：299 元/月。毛利率：80%。" },
          { text: "您每周每个客户只需花费 5-10 分钟同步进度。极其高效。" },
        ],
      },
    ],
  },
  cta: createSolutionCta("加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。"),
}) satisfies TeamSolutionContent;

const TEAM_SOLUTION_PAGES: Record<TeamSolutionSlug, TeamSolutionContent> = {
  agencies: agenciesPage,
  enterprise: enterprisePage,
  "pr-brand-teams": prBrandPage,
  "smb-geo-teams": smbGeoPage,
  "seo-specialists": seoSpecialistsPage,
};

export function getTeamSolutionPage(slug: string): TeamSolutionContent | null {
  if (!(TEAM_SOLUTION_SLUGS as readonly string[]).includes(slug)) return null;
  return TEAM_SOLUTION_PAGES[slug as TeamSolutionSlug];
}

export function getAllTeamSolutionPages(): TeamSolutionContent[] {
  return TEAM_SOLUTION_SLUGS.map((slug) => TEAM_SOLUTION_PAGES[slug]);
}

export function teamSolutionFaqsDefault(slug: TeamSolutionSlug): Faq[] {
  return resolveFaqDefaults([...teamSolutionFaqDefaultsBySlug[slug]]);
}

export function mergeTeamSolutionFaqs(
  slug: TeamSolutionSlug,
  cms: FaqDoc[] | null | undefined,
): Faq[] {
  return mergeFaqs(cms, teamSolutionFaqsDefault(slug));
}

export function teamSolutionFaqPageKey(slug: TeamSolutionSlug): string {
  return teamSolutionFaqPage(slug);
}

export { TEAM_SOLUTION_SLUGS };
