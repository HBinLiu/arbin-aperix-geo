import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchOverview } from "@/api/analysis";
import { cn } from "@/lib/utils";
import { useSubjectPipeline } from "@/hooks/useSubjectPipeline";
import {
  defaultDateRange,
  formatRate,
  formatRank,
  formatScore,
} from "@/lib/analysis";
import type { OverviewMetrics } from "@/types";
import { queryKeys } from "@/lib/queries";

type PipelineStep = {
  id: string;
  title: string;
  subtitle: string;
  status: "done" | "processing" | "queue";
};

const STAGE_ORDER = ["verify", "dispatch", "clean", "analyze"] as const;

function stepStatusForStage(
  stepStage: (typeof STAGE_ORDER)[number],
  currentStage: string,
): PipelineStep["status"] {
  const currentIdx = STAGE_ORDER.indexOf(currentStage as (typeof STAGE_ORDER)[number]);
  const stepIdx = STAGE_ORDER.indexOf(stepStage);
  if (currentIdx < 0) return stepIdx === 0 ? "done" : "queue";
  if (stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "processing";
  return "queue";
}

function StepStatusBadge({ status }: { status: PipelineStep["status"] }) {
  if (status === "done") {
    return (
      <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-emerald-600">
        完成
      </span>
    );
  }
  if (status === "processing") {
    return (
      <span className="bg-primary/10 text-primary rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide">
        进行中
      </span>
    );
  }
  return (
    <span className="text-muted-foreground rounded bg-muted px-2 py-0.5 text-[10px] font-semibold tracking-wide">
      等待
    </span>
  );
}

function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="border-border bg-card rounded-lg border p-4">
      <p className="text-muted-foreground text-xs font-medium">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      {hint ? <p className="text-muted-foreground mt-1 text-[11px]">{hint}</p> : null}
    </div>
  );
}

function KpiSkeleton() {
  return <div className="bg-muted h-[88px] animate-pulse rounded-lg" />;
}

function buildSteps(stage: string, jobProgress?: number): PipelineStep[] {
  return [
    {
      id: "verify",
      title: "品牌信息验证",
      subtitle: "主体、竞品、主题与提示词已确认",
      status: stepStatusForStage("verify", stage),
    },
    {
      id: "dispatch",
      title: "大模型任务调度",
      subtitle: jobProgress != null ? `采样进度 ${jobProgress}%` : "向大模型批量发起质询",
      status: stepStatusForStage("dispatch", stage),
    },
    {
      id: "clean",
      title: "语义清洗降噪",
      subtitle: "从原始回答提取结构化信号",
      status: stepStatusForStage("clean", stage),
    },
    {
      id: "analyze",
      title: "声量聚合诊断",
      subtitle: "计算六大 KPI 并生成看板",
      status: stepStatusForStage("analyze", stage),
    },
  ];
}

function overviewToKpis(data: OverviewMetrics | undefined) {
  if (!data || data.response_count === 0) return null;
  return [
    { label: "可见度", value: formatRate(data.visibility_rate) },
    { label: "AI 提及", value: formatScore(data.mention_intensity) },
    { label: "声量份额", value: formatRate(data.share_of_voice) },
    { label: "平均排名", value: formatRank(data.average_rank) },
    { label: "引用率", value: formatRate(data.citation_rate) },
    { label: "情感倾向", value: formatScore(data.sentiment_score) },
  ];
}

type OverviewContentProps = {
  subjectId: string;
};

/** 控制台概述：四步流水线进度 + 六大 KPI。 */
export function OverviewContent({ subjectId }: OverviewContentProps) {
  const { from, to } = useMemo(() => defaultDateRange(), []);
  const {
    stage,
    job,
    jobProgress,
    processedItems,
    totalItems,
    canShowMetrics,
    currentStepIdx,
    isFailed,
  } = useSubjectPipeline(subjectId);

  const overviewQuery = useQuery({
    queryKey: queryKeys.overview(subjectId, from, to),
    queryFn: () => fetchOverview(subjectId, from, to),
    enabled: canShowMetrics,
  });

  const steps = buildSteps(stage, jobProgress);
  const kpis = overviewToKpis(overviewQuery.data);

  return (
    <div className="flex h-full flex-col px-4 py-3 sm:px-5">
      <div className="bg-accent/70 text-foreground mb-4 rounded-md px-3 py-2 text-sm">
        诊断流水线：第 {Math.max(1, currentStepIdx + 1)}/4 阶段
        {totalItems > 0 ? (
          <span className="text-muted-foreground ml-2 text-xs">
            已完成 {processedItems}/{totalItems} 条采样
          </span>
        ) : null}
        {isFailed && job?.error_message ? (
          <span className="text-destructive ml-2 text-xs">{job.error_message}</span>
        ) : null}
      </div>

      <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,18rem)]">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">核心指标</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            近 30 天、全部渠道的成功回复聚合（{overviewQuery.data?.response_count ?? 0} 条）
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {overviewQuery.isLoading || (canShowMetrics && !kpis)
              ? Array.from({ length: 6 }).map((_, i) => <KpiSkeleton key={i} />)
              : kpis
                ? kpis.map((k) => <KpiCard key={k.label} label={k.label} value={k.value} />)
                : Array.from({ length: 6 }).map((_, i) => (
                    <KpiCard key={i} label="—" value="诊断进行中" />
                  ))}
          </div>
        </div>

        <ol className="space-y-4">
          {steps.map((step, index) => (
            <li key={step.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={cn(
                    "flex size-6 items-center justify-center rounded-full text-[11px] font-semibold",
                    step.status === "done"
                      ? "bg-emerald-100 text-emerald-700"
                      : step.status === "processing"
                        ? "bg-primary/15 text-primary"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {index + 1}
                </span>
                {index < steps.length - 1 ? (
                  <span className="bg-border mt-1 h-full min-h-6 w-px" aria-hidden />
                ) : null}
              </div>
              <div className="min-w-0 flex-1 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium leading-snug">{step.title}</p>
                    <p className="text-muted-foreground mt-0.5 text-xs">{step.subtitle}</p>
                  </div>
                  <StepStatusBadge status={step.status} />
                </div>
                {step.status === "processing" && jobProgress != null ? (
                  <div className="bg-muted mt-2 h-1.5 overflow-hidden rounded-full">
                    <div
                      className="bg-primary h-full rounded-full transition-all"
                      style={{ width: `${jobProgress}%` }}
                    />
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
