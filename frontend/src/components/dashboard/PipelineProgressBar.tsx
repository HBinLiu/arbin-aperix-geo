import { PipelineProgressShimmer } from "@/components/dashboard/PipelineProgressShimmer";
import { cn } from "@/lib/utils";

type PipelineProgressBarProps = {
  value: number;
  active?: boolean;
  failed?: boolean;
  done?: boolean;
  trackClassName?: string;
  fillClassName?: string;
  heightClass?: string;
  ariaLabel: string;
};

export function PipelineProgressBar({
  value,
  active = false,
  failed = false,
  done = false,
  trackClassName,
  fillClassName,
  heightClass = "h-1.5",
  ariaLabel,
}: PipelineProgressBarProps) {
  return (
    <div
      className={cn(
        "bg-background overflow-hidden rounded-full",
        active && "ring-primary/15 ring-1",
        trackClassName,
      )}
    >
      <div
        className={cn(
          "relative overflow-hidden rounded-full transition-all duration-700 ease-out",
          heightClass,
          done && "bg-emerald-500",
          active && "bg-primary pipeline-progress-glow-pulse",
          failed && "bg-error",
          !active && !done && !failed && "bg-transparent",
          fillClassName,
        )}
        style={{ width: `${value}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={ariaLabel}
      >
        {active ? <PipelineProgressShimmer /> : null}
      </div>
    </div>
  );
}
