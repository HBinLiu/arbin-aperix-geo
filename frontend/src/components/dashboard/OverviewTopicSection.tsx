import { TopicPerformanceTable } from "@/components/analysis/prompt/TopicPerformanceTable";
import type { TopicPerformanceRow } from "@/lib/analysis/prompt";
import { cn } from "@/lib/utils";

const TITLE = "主题表现";
const DESCRIPTION =
  "展示品牌在所跟踪提示词下 AI 生成答案中的整体表现，帮助您直观地了解品牌表现及其趋势变化。";

type OverviewTopicSectionProps = {
  rows: TopicPerformanceRow[];
  loading?: boolean;
  className?: string;
};

/** 概述页 · 主题表现表 */
export function OverviewTopicSection({
  rows,
  loading = false,
  className,
}: OverviewTopicSectionProps) {
  return (
    <section
      className={cn(
        "border-border w-full overflow-hidden rounded-lg border bg-muted-background",
        className,
      )}
      aria-busy={loading}
      aria-label={loading ? "加载主题表现" : undefined}
    >
      <header className="border-border border-b px-5 py-4">
        <h2 className="text-base font-semibold tracking-tight">{TITLE}</h2>
        <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">{DESCRIPTION}</p>
      </header>
      <TopicPerformanceTable rows={rows} loading={loading} className="border-0 rounded-none" />
    </section>
  );
}
