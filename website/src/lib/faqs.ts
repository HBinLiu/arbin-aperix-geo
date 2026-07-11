import type { Faq, FaqDoc } from "@shared/faq";
import { richTextToHtml } from "@/lib/lexical";
import { resolveSiteCopy } from "@/lib/site";

function toFaq(input: { question: string; answerHtml: string; label?: string }): Faq {
  const faq: Faq = {
    question: resolveSiteCopy(input.question.trim()),
    answerHtml: resolveSiteCopy(input.answerHtml),
  };
  const label = input.label?.trim();
  if (label) faq.label = resolveSiteCopy(label);
  return faq;
}

function normalizeFaqDoc(item: FaqDoc): Faq | null {
  if (!item.question.trim() || !item.answer) return null;
  const answerHtml = richTextToHtml(item.answer);
  if (!answerHtml.trim()) return null;
  return toFaq({
    question: item.question,
    answerHtml,
    label: item.label ?? undefined,
  });
}

/** 静态默认 FAQ：替换占位符 */
export function resolveFaqDefaults(defaults: Faq[]): Faq[] {
  return defaults.map(toFaq);
}

/** CMS FAQ 与静态兜底合并；CMS 有数据时优先使用 */
export function mergeFaqs(cms: FaqDoc[] | null | undefined, defaults: Faq[]): Faq[] {
  const items =
    cms?.map(normalizeFaqDoc).filter((item): item is Faq => item !== null) ?? [];
  return items.length > 0 ? items : [...defaults];
}

export type { Faq, FaqDoc } from "@shared/faq";
export { faqAnswerText } from "@shared/faq";
