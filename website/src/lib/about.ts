import type { CmsAboutPage } from "@/lib/payload";
import { richTextToHtml } from "@/lib/lexical";
import { resolveSiteCopy, resolveSiteCopyDeep } from "@/lib/site";
import { ABOUT_STORY_PARAGRAPHS, ABOUT_STORY_TITLE } from "@shared/about";
import { faqP } from "@shared/faq/html";

export const aboutHero = resolveSiteCopyDeep({
  titleBefore: "About ",
  titleHighlight: "{{siteName}}",
  tagline: "我们正在构建 AI 时代品牌可见性的未来。",
  mission: "我们的使命是不仅让品牌被看见，更让品牌获得 AI 系统的信任。",
});

export const aboutStoryFallbackHtml = faqP(
  ...resolveSiteCopyDeep([...ABOUT_STORY_PARAGRAPHS]),
);

export type AboutStory = {
  title: string;
  bodyHtml: string;
};

export function mergeAboutStory(cms: CmsAboutPage | null | undefined): AboutStory {
  const cmsHtml = richTextToHtml(cms?.story?.content);

  return {
    title: resolveSiteCopy(cms?.story?.title?.trim() || ABOUT_STORY_TITLE),
    bodyHtml: cmsHtml.trim() ? cmsHtml : aboutStoryFallbackHtml,
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
