import { cn } from "@/lib/utils";

type ProgressBarProps = {
  value: number;
  max: number;
  segments?: number;
  className?: string;
};

/** 分段进度条（用于额度/用量展示） */
export function ProgressBar({
  value,
  max,
  segments = 10,
  className,
}: ProgressBarProps) {
  const ratio = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
  const filled = Math.round(ratio * segments);

  return (
    <div className={cn("flex gap-1", className)} aria-hidden>
      {Array.from({ length: segments }, (_, index) => (
        <div
          key={index}
          className={cn(
            "h-1.5 min-w-0 flex-1 rounded-sm",
            index < filled ? "bg-primary" : "bg-background",
          )}
        />
      ))}
    </div>
  );
}
