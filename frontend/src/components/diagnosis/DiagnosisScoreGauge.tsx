import { cn } from "@/lib/utils";
import { DIAGNOSIS_STATUS_LABELS } from "@/lib/diagnosis";
import type { DiagnosisStatus } from "@/types";
import { TextBadge, type SemanticBadgeVariant } from "@/components/ui/badge";

type DiagnosisScoreGaugeProps = {
  score: number;
  status: DiagnosisStatus;
  loading?: boolean;
  className?: string;
};

const STATUS_BADGE_VARIANT: Record<DiagnosisStatus, SemanticBadgeVariant> = {
  excellent: "success",
  good: "success",
  needs_improvement: "warning",
  critical: "error",
};

function formatDiagnosisScore(value: number): string {
  return String(Number(value.toFixed(2)));
}

/** 诊断得分半圆仪表 */
export function DiagnosisScoreGauge({
  score,
  status,
  loading = false,
  className,
}: DiagnosisScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(score, 100));
  const angle = (clamped / 100) * 180;
  const radius = 72;
  const cx = 100;
  const cy = 92;
  const startX = cx - radius;
  const endX = cx + radius;
  const arcPath = `M ${startX} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${cy}`;

  return (
    <div
      className={cn(
        "border-border flex min-h-[220px] flex-col rounded-lg border bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        className,
      )}
      aria-busy={loading}
    >
      <h3 className="text-sm font-medium">诊断得分</h3>

      <div className="relative mx-auto mt-2 flex w-full max-w-[220px] flex-1 flex-col items-center justify-center">
        {loading ? (
          <div className="bg-muted size-28 animate-pulse rounded-full" />
        ) : (
          <>
            <svg viewBox="0 0 200 120" className="h-auto w-full" aria-hidden>
              <path
                d={arcPath}
                fill="none"
                stroke="currentColor"
                strokeWidth="14"
                strokeLinecap="round"
                className="text-muted-foreground/10"
              />
              <path
                d={arcPath}
                fill="none"
                stroke="currentColor"
                strokeWidth="14"
                strokeLinecap="round"
                pathLength={180}
                strokeDasharray={`${angle} 180`}
                className="text-primary"
              />
            </svg>
            <div className="absolute inset-x-0 bottom-6 text-center">
              <p className="text-2xl font-bold tracking-tight tabular-nums">
                {formatDiagnosisScore(score)}
                <span className="text-muted-foreground text-base font-medium"> / 100</span>
              </p>
              <TextBadge
                variant={STATUS_BADGE_VARIANT[status]}
                className="mt-2 rounded-full px-2.5 py-0.5 text-xs font-medium"
              >
                {DIAGNOSIS_STATUS_LABELS[status]}
              </TextBadge>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
