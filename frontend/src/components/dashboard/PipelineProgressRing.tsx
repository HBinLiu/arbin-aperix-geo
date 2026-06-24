import { PipelineProgressShimmer } from "@/components/dashboard/PipelineProgressShimmer";
import { cn } from "@/lib/utils";

type PipelineProgressRingProps = {
  value: number;
  className?: string;
  label?: string;
};

const RING_MASK =
  "radial-gradient(circle, transparent 46px, black 50px, black 58px, transparent 62px)";

export function PipelineProgressRing({ value, className, label }: PipelineProgressRingProps) {
  const clamped = Math.min(100, Math.max(0, value));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const showShimmer = clamped > 0 && clamped < 100;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg
        width="128"
        height="128"
        viewBox="0 0 128 128"
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-muted/80"
        />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="text-primary transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>

      {showShimmer ? (
        <div
          className="pointer-events-none absolute inset-0 overflow-hidden rounded-full"
          style={{
            maskImage: RING_MASK,
            WebkitMaskImage: RING_MASK,
          }}
          aria-hidden
        >
          <PipelineProgressShimmer />
        </div>
      ) : null}

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">{clamped}%</span>
        {label ? (
          <span className="text-muted-foreground mt-0.5 text-[11px]">{label}</span>
        ) : null}
      </div>
    </div>
  );
}
