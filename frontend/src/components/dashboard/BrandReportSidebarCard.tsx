import { useState } from "react";
import { FileText } from "lucide-react";

import { BrandReportDialog } from "@/components/dashboard/BrandReportDialog";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import type { SubjectPipelineState } from "@/hooks/useSubjectPipeline";
import { cn } from "@/lib/utils";

type BrandReportSidebarCardProps = {
  pipeline: SubjectPipelineState;
};

export function BrandReportSidebarCard({ pipeline }: BrandReportSidebarCardProps) {
  const { subject } = useDashboardContext();
  const [open, setOpen] = useState(false);
  const canOpen = pipeline.canShowMetrics && !pipeline.isFailed;

  const brandName = subject.brand?.trim() || subject.domain?.trim() || "品牌";

  const hint = pipeline.isFailed
    ? "采样失败，请先在概述页重试后再导出报告。"
    : !pipeline.canShowMetrics
      ? "品牌分析完成后，可选择时间范围预览并导出 PDF。"
      : "选择时间范围预览并导出 PDF，可随时重复生成。";

  return (
    <>
      <div className="relative shrink-0">
        <div className="border-border/80 rounded-lg border bg-white p-3 shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)]">
          <div className="flex items-start gap-2.5">
            <span className="bg-primary/10 text-primary mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg">
              <FileText className="size-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-medium">品牌分析报告</p>
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{hint}</p>
              <button
                type="button"
                className={cn(
                  "mt-2.5 inline-flex h-8 items-center justify-center rounded-md px-3 text-xs font-medium transition-colors",
                  canOpen
                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                    : "bg-muted text-muted-foreground cursor-not-allowed",
                )}
                disabled={!canOpen}
                onClick={() => setOpen(true)}
              >
                查看报告
              </button>
            </div>
          </div>
        </div>
      </div>

      {canOpen ? (
        <BrandReportDialog
          open={open}
          onOpenChange={setOpen}
          subjectId={subject.id}
          brandName={brandName}
        />
      ) : null}
    </>
  );
}
