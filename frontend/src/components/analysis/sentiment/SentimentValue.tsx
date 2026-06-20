import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { sentimentDisplayLabel } from "@/lib/analysis/sentiment";
import { cn } from "@/lib/utils";

export function sentimentDotVariant(label: string): SemanticBadgeVariant {
  if (label === "正面") return "success";
  if (label === "负面") return "error";
  return "warning";
}

export type SentimentValueProps = {
  /** 展示分值或文案 */
  value: string;
  /** 后端 sentiment_label（positive / neutral / negative） */
  label?: string | null;
  className?: string;
};

function sentimentToneLabel(value: string, label?: string | null): string {
  if (label != null && label !== "") {
    return sentimentDisplayLabel(label);
  }
  return value;
}

/** 表格单元格：DotBadge（当前分值 + 标签配色） */
export function SentimentValue({ value, label, className }: SentimentValueProps) {
  const toneLabel = sentimentToneLabel(value, label);

  return (
    <div className={cn("inline-flex items-center tabular-nums", className)}>
      <DotBadge variant={sentimentDotVariant(toneLabel)}>
        {value}
      </DotBadge>
    </div>
  );
}
