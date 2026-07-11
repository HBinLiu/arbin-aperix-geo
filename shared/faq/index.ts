import type { FaqPageKey } from "./pages";

/** CMS FAQ 单条（`FaqPageDoc.items` 元素；answer 为 Payload Lexical JSON） */
export type FaqDoc = {
  question: string;
  answer: unknown;
  /** 平台/定价 FAQ 左侧分类码（如「方法」「提示词」） */
  label?: string | null;
};

/** CMS FAQ 页面文档（每页一条） */
export type FaqPageDoc = {
  page: FaqPageKey;
  label?: string | null;
  items?: FaqDoc[] | null;
};

/** 官网 FAQ */
export type Faq = {
  question: string;
  answerHtml: string;
  /** 可选；PlatformFaqSection 展示为 /// {label}，序号由组件按 index 生成 */
  label?: string;
};

/** JSON-LD 纯文本 */
export function faqAnswerText(faq: Faq): string {
  return faq.answerHtml
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
