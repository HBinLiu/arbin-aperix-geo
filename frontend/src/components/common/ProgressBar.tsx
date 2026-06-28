import { cn } from "@/lib/utils";

type ProgressBarProps = {
  value: number;
  max: number;
  /** 不传则按 max 自动计算（≤10 与 max 同格数，否则 10 格） */
  segments?: number;
  className?: string;
};

function resolveSegmentCount(max: number): number {
  if (max <= 0) return 1;
  if (max <= 10) return max;
  return 10;
}

/** 分段进度条（用于额度/用量展示） */
export function ProgressBar({
  value,
  max,
  segments: segmentsOverride,
  className,
}: ProgressBarProps) {
  const segments = segmentsOverride ?? resolveSegmentCount(max);
  const ratio = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;

  return (
    <div className={cn("w-full space-y-1.5", className)} aria-hidden>
      <div className="border-border h-3.5 w-full rounded-[4px] border p-0.5">
        <div
          className="grid h-full w-full gap-1"
          style={{ gridTemplateColumns: `repeat(${segments}, minmax(0px, 1fr))` }}
        >
          {Array.from({ length: segments }, (_, index) => {
            const fillPercent = Math.min(Math.max(ratio * segments - index, 0), 1) * 100;
            return (
              <span key={index} className="bg-background relative h-full overflow-hidden rounded-[2px]">
                <span
                  className="absolute inset-y-0 left-0 rounded-[2px] bg-primary transition-[width,background-color]"
                  style={{ width: `${fillPercent}%` }}
                />
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
