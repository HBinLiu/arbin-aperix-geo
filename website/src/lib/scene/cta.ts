import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";
import type { SceneSlug } from "@shared/faq/pages";
import { appLinks } from "@/lib/app-links";

const sceneCtaDefaults = {
  badge: "准备就绪",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: appLinks.register,
  primaryCtaLabel: "开始注册试用",
  primaryCtaHref: appLinks.register,
} satisfies Partial<CtaContent>;

type SceneCtaFields = Pick<
  CtaContent,
  "titleBefore" | "titleHighlight" | "titleAfter" | "description"
> &
  Partial<Omit<CtaContent, "titleBefore" | "titleHighlight" | "titleAfter" | "description">>;

/** 组装单页 CTA；未传入字段沿用 scene 通用默认值 */
export function createSceneCta(fields: SceneCtaFields): CtaContent {
  return resolveSiteCopyDeep({
    ...sceneCtaDefaults,
    ...fields,
  });
}

/** 各使用场景页底部 CTA（标题、描述、代码行可按页定制） */
export const sceneCtaBySlug = {
  "product-launch": createSceneCta({
    titleBefore: "准备好让新产品",
    titleHighlight: "从第一天起",
    titleAfter: "被 AI 引用了吗？",
    description: "加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。",
    codeLines: ["// 发布即被看见。", "// 不再沉默消亡。"],
  }),
  "narrative-shaping": createSceneCta({
    titleBefore: "准备好塑造",
    titleHighlight: "品牌叙事",
    titleAfter: "了吗？",
    description: "加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。",
    codeLines: ["// 定义你的故事。", "// 让 AI 替你讲述。"],
  }),
  "content-strategy": createSceneCta({
    titleBefore: "准备好统一",
    titleHighlight: "内容叙事",
    titleAfter: "了吗？",
    description: "加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。",
    codeLines: ["// 对齐每一触点。", "// 强化 AI 记忆。"],
  }),
  "competitive-positioning": createSceneCta({
    titleBefore: "准备好夺回",
    titleHighlight: "竞争份额",
    titleAfter: "了吗？",
    description: "加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。",
    codeLines: ["// 洞察对手叙事。", "// 赢得 AI 推荐。"],
  }),
  "brand-crisis-management": createSceneCta({
    titleBefore: "准备好保护",
    titleHighlight: "品牌声誉",
    titleAfter: "了吗？",
    description: "加入 2,000+ 营销团队，共同追踪 AI 搜索可见度。 基于数据洞察，告别盲目优化。",
    codeLines: ["// 24/7 声誉监测。", "// 危机前先行动。"],
  }),
} satisfies Record<SceneSlug, CtaContent>;

export function sceneCta(slug: SceneSlug): CtaContent {
  return sceneCtaBySlug[slug];
}
