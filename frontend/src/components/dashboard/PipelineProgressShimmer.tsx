import { cn } from "@/lib/utils";

type PipelineProgressShimmerProps = {
  className?: string;
};

export function PipelineProgressShimmer({ className }: PipelineProgressShimmerProps) {
  return (
    <span
      className={cn(
        "pipeline-progress-shimmer pointer-events-none absolute inset-y-0 w-2/3 bg-gradient-to-r from-transparent via-surface/55 to-transparent",
        className,
      )}
      aria-hidden
    />
  );
}
