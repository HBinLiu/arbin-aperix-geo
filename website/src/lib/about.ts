import type { CmsPage } from "@/lib/payload";

export const aboutHero = {
  titleBefore: "About ",
  titleHighlight: "{{name}}",
  tagline: "我们正在构建 AI 时代品牌可见性的未来。",
  mission: "我们的使命是不仅让品牌被看见，更让品牌获得 AI 系统的信任。",
};

export const aboutStory = {
  title: "我们的故事",
  paragraphs: [
    "{{name}} 的起点是一支专注 GEO 与 AI 营销的数据与工程团队。我们长期为国内主流 AI 平台构建监测、分析与指标体系——从采集、清洗、建模，到可见度监控与竞品对标。也正因为站在「数据底座」的位置，我们很早就看清了一个变化：用户正在从「搜索列表」转向「AI 直接给答案」。",
    "在 AI 搜索里，竞争不再是「排第几」，而是：AI 会不会看到你、信不信你、推不推荐你、引不引用你。很多品牌在传统渠道里表现不错，但在豆包、DeepSeek、通义千问等平台上却变得「隐形」：AI 知道品牌存在，却很少主动推荐。",
    "我们创建 {{name}}，就是为了把这件事从「猜测」变成「可决策」。{{name}} 是一个面向国内 AI 平台的 GEO 数据策略层：用 AI 可见度与引用数据，识别品牌在关键决策问题中的缺口、被竞品截流的场景，以及真正影响 AI 推荐的信源结构；再把这些洞察转化为可执行的优化路径。",
    "我们也相信，在这个时代「执行的自动化」会越来越廉价，真正难的是策略与上下文。{{name}} 不绑定某一个内容工具，而是通过可插拔的能力体系，把成熟的 GEO 与增长经验沉淀在平台上，让团队用最合适的工具去执行，但始终由同一套数据与指标驱动决策。",
    "我们的目标客户是需要规模化获客的团队：B2B SaaS 与 PLG 团队、电商与 DTC 品牌，以及为客户交付增长的 Agency 与专业服务团队。我们希望帮助他们在 AI 时代建立可被理解、可被信任、可被推荐的品牌资产，并用更低试错成本持续优化。",
  ],
} as const;

export type AboutStory = {
  title: string;
  paragraphs: string[];
};

export function mergeAboutStory(cms: CmsPage | null | undefined): AboutStory {
  const paragraphs =
    cms?.story?.paragraphs
      ?.map((item) => item.text.trim())
      .filter((text) => text.length > 0) ?? [];

  return {
    title: cms?.story?.title?.trim() || aboutStory.title,
    paragraphs: paragraphs.length > 0 ? paragraphs : [...aboutStory.paragraphs],
  };
}

export type AboutValueIcon = "customer" | "trust" | "innovation" | "team";

export type AboutValueItem = {
  icon: AboutValueIcon;
  title: string;
  description: string;
};

export const aboutValues = {
  title: "我们的价值观",
  items: [
    {
      icon: "customer",
      title: "以客户为中心",
      description: "我们致力于解决客户每天面临的真实问题。",
    },
    {
      icon: "trust",
      title: "信任与透明",
      description: "我们相信真实的数据和清晰的洞察，而非虚荣指标。",
    },
    {
      icon: "innovation",
      title: "创新优先",
      description: "我们保持在 AI 发展曲线的前沿，交付尖端解决方案。",
    },
    {
      icon: "team",
      title: "卓越团队",
      description: "我们聘请最优秀的人才，并赋能他们做到最好。",
    },
  ] satisfies AboutValueItem[],
};
