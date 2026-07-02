import { useMemo } from "react";
import { Zap } from "lucide-react";
import { Link } from "react-router-dom";

import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import { Button } from "@/components/ui/button";
import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useDiagnosisContent } from "@/hooks/useDiagnosisContent";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import {
  diagnosisPriorityActionSummary,
  type DiagnosisContentRow,
} from "@/lib/diagnosis/content";
import { DIAGNOSIS_BASE_PATH, diagnosisContentDetailPath } from "@/lib/diagnosis/nav";
import type { AnalysisEntityRef, AnalysisFilters, OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

const TOP_ACTIONS_PAGE_SIZE = 3;

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

type OverviewPrioritySectionProps = {
  subjectId: string;
  filters: AnalysisFilters;
  className?: string;
};

function PriorityActionRow({
  row,
  rank,
  entities,
}: {
  row: DiagnosisContentRow;
  rank: number;
  entities: AnalysisEntityRef[];
}) {
  const competitors = row.competitors;
  const summary = diagnosisPriorityActionSummary(row, entities);

  return (
    <article className="border-border flex items-center gap-3 rounded-lg border px-4 py-3">
      <span
        className="bg-background text-muted-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums"
        aria-hidden
      >
        {rank}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <p className="text-foreground min-w-0 truncate text-sm font-semibold">{row.promptText}</p>
          <DotBadge
            variant={PRIORITY_VARIANT[row.priority]}
            className="shrink-0 px-2 py-0.5 text-xs"
          >
            {row.priorityLabel}
          </DotBadge>
        </div>
        <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2">
          {competitors.length > 0 ? (
            <MentionedBrandsCell brands={competitors} />
          ) : null}
          <span className="text-muted-foreground min-w-0 text-xs leading-relaxed">{summary}</span>
        </div>
      </div>

      <Button asChild size="sm" className="shrink-0">
        <Link to={diagnosisContentDetailPath(row.promptId)}>AI 写内容 →</Link>
      </Button>
    </article>
  );
}

function PriorityActionSkeletonRows() {
  return (
    <>
      {Array.from({ length: TOP_ACTIONS_PAGE_SIZE }).map((_, index) => (
        <div
          key={index}
          className="border-border flex items-center gap-3 rounded-lg border bg-background px-4 py-3"
          aria-hidden
        >
          <Skeleton className="size-7 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-4 w-full max-w-md" />
            <Skeleton className="h-3 w-full max-w-lg" />
          </div>
          <Skeleton className="h-8 w-24 shrink-0 rounded-md" />
        </div>
      ))}
    </>
  );
}

/** 概述页 · 本周 Top 3 优先行动（诊断中心数据） */
export function OverviewPrioritySection({
  subjectId,
  filters,
  className,
}: OverviewPrioritySectionProps) {
  const listRequest = useMemo(
    () => ({ page: 1, pageSize: TOP_ACTIONS_PAGE_SIZE }),
    [],
  );

  const { entities } = useAnalysisFilter();
  const { loading, rows } = useDiagnosisContent(subjectId, filters, listRequest);

  if (!loading && rows.length === 0) {
    return null;
  }

  return (
    <section
      className={cn(
        "border-border w-full overflow-hidden rounded-lg border bg-muted-background",
        className,
      )}
      aria-busy={loading}
      aria-label={loading ? "加载优先行动" : "本周 Top 3 优先行动"}
    >
      <header className="flex items-center justify-between gap-3 px-5 py-4">
        <div className="flex min-w-0 items-center gap-2">
          <Zap className="text-primary size-4 shrink-0" aria-hidden />
          <h2 className="text-base font-semibold tracking-tight">本周 Top 3 优先行动</h2>
        </div>
        <Link
          to={DIAGNOSIS_BASE_PATH}
          className="text-muted-foreground hover:text-foreground shrink-0 text-sm font-medium transition-colors"
        >
          查看全部 →
        </Link>
      </header>

      <div className="flex flex-col gap-3 px-5 pb-5">
        {loading && rows.length === 0 ? (
          <PriorityActionSkeletonRows />
        ) : (
          rows.map((row, index) => (
            <PriorityActionRow key={row.id} row={row} rank={index + 1} entities={entities} />
          ))
        )}
      </div>
    </section>
  );
}
