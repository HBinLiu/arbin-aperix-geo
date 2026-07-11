/**
 * 官网 CMS 默认内容（含 {{name}} 占位符，与 website/src/lib 静态兜底一致）。
 */

export const defaultAboutPage = {
  _status: "published" as const,
  seo: {
    title: "关于我们 | {{name}}",
    description:
      "{{name}} 是一家专注于生成式引擎优化的公司，致力于帮助品牌建立真实的 AI 信任与影响力。我们连接 SEO 与 GEO，让每个企业都能获得 AI 可见性。了解我们的故事。",
  },
  story: {
    title: "我们的故事",
    paragraphs: [
      {
        text: "{{name}} 的起点是一支专注 GEO 与 AI 营销的数据与工程团队。我们长期为国内主流 AI 平台构建监测、分析与指标体系——从采集、清洗、建模，到可见度监控与竞品对标。也正因为站在「数据底座」的位置，我们很早就看清了一个变化：用户正在从「搜索列表」转向「AI 直接给答案」。",
      },
      {
        text: "在 AI 搜索里，竞争不再是「排第几」，而是：AI 会不会看到你、信不信你、推不推荐你、引不引用你。很多品牌在传统渠道里表现不错，但在豆包、DeepSeek、通义千问等平台上却变得「隐形」：AI 知道品牌存在，却很少主动推荐。",
      },
      {
        text: "我们创建 {{name}}，就是为了把这件事从「猜测」变成「可决策」。{{name}} 是一个面向国内 AI 平台的 GEO 数据策略层：用 AI 可见度与引用数据，识别品牌在关键决策问题中的缺口、被竞品截流的场景，以及真正影响 AI 推荐的信源结构；再把这些洞察转化为可执行的优化路径。",
      },
      {
        text: "我们也相信，在这个时代「执行的自动化」会越来越廉价，真正难的是策略与上下文。{{name}} 不绑定某一个内容工具，而是通过可插拔的能力体系，把成熟的 GEO 与增长经验沉淀在平台上，让团队用最合适的工具去执行，但始终由同一套数据与指标驱动决策。",
      },
      {
        text: "我们的目标客户是需要规模化获客的团队：B2B SaaS 与 PLG 团队、电商与 DTC 品牌，以及为客户交付增长的 Agency 与专业服务团队。我们希望帮助他们在 AI 时代建立可被理解、可被信任、可被推荐的品牌资产，并用更低试错成本持续优化。",
      },
    ],
  },
};

export type DefaultHomeFaq = {
  question: string;
  answer: string;
  sortOrder: number;
};

export const defaultHomeFaqs: DefaultHomeFaq[] = [
  {
    question: "GEO 和 SEO 有什么区别？",
    answer:
      "SEO 针对搜索引擎排名进行优化。GEO（生成引擎优化）针对 AI 模型的引用和推荐进行优化。两者对于全面的品牌可见性都至关重要。",
    sortOrder: 0,
  },
  {
    question: "{{name}} 与其他 GEO 工具有什么不同？",
    answer:
      "我们关注信任，而不仅仅是可见性。我们为您展示排名位置、情感分析和可执行的建议，而不仅仅是提及次数。",
    sortOrder: 1,
  },
  {
    question: "支持哪些 AI 模型？",
    answer:
      "国内主流大模型：豆包、DeepSeek、通义千问、腾讯元宝、Kimi、文心一言均已支持 —— 更多模型正在持续添加中。",
    sortOrder: 2,
  },
  {
    question: "多久能看到效果？",
    answer:
      "趋势可见性需要 2-4 周，可落地洞察需要 4-8 周。AI 模型的更新速度与搜索引擎不同。我们同样也提供针对中大型企业的GEO/SEO优化服务，帮助您直接达成流量/AI可见度的目标，直接交付结果。",
    sortOrder: 3,
  },
];
