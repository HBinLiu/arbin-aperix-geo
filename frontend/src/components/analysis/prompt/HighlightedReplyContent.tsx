import {
  responseMentionedBrandTerms,
  type ResponseMentionTerm,
} from "@/lib/analysis/responseDetail";
import type { LlmResponseParsed } from "@/types";

import { ReplyMarkdownContent } from "./ReplyMarkdownContent";

type HighlightedReplyContentProps = {
  text: string;
  parsed: LlmResponseParsed | null | undefined;
  mentionTerms?: ResponseMentionTerm[];
  className?: string;
};

/** AI 回复正文：Markdown + 提及品牌 inline 标记 */
export function HighlightedReplyContent({
  text,
  parsed,
  mentionTerms,
  className,
}: HighlightedReplyContentProps) {
  const terms = mentionTerms ?? responseMentionedBrandTerms(parsed);
  if (!text.trim()) {
    return <p className="text-muted-foreground text-sm">暂无回复正文</p>;
  }
  return <ReplyMarkdownContent text={text} mentionTerms={terms} className={className} />;
}
