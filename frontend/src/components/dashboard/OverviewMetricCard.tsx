import { Info } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type OverviewMetricCardProps = {
  title: string;
  description: string;
  value: string;
  rankSubtitle?: string | null;
  /** 右下角标签：排名序号或「可提升」 */
  tag?: { type: "rank"; rank: number } | { type: "improve" } | null;
  loading?: boolean;
  className?: string;
};

function MetricTitleInfo({ title, description }: { title: string; description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`了解${title}`}
          onClick={() => setOpen((prev) => !prev)}
        >
          <Info className="size-4" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="w-[250px] min-w-[250px] max-w-[250px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        <p className="w-full text-wrap">{description}</p>
      </TooltipContent>
    </Tooltip>
  );
}

export function OverviewMetricCard({
  title,
  description,
  value,
  rankSubtitle,
  tag,
  loading = false,
  className,
}: OverviewMetricCardProps) {
  return (
    <div
      className={cn(
        "border-border relative flex min-h-[120px] flex-col rounded-lg border bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        className,
      )}
      aria-busy={loading}
    >
      <div className="flex items-center gap-1.5">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        <MetricTitleInfo title={title} description={description} />
      </div>

      {loading ? (
        <div className="bg-muted mt-4 h-8 w-20 animate-pulse rounded-md" />
      ) : (
        <p className="mt-3 text-2xl font-bold tracking-tight tabular-nums">{value}</p>
      )}

      <div className="mt-auto flex items-end justify-between gap-2 pt-4">
        {loading ? (
          <div className="bg-muted h-4 w-28 animate-pulse rounded" />
        ) : rankSubtitle ? (
          <p className="text-muted-foreground flex min-w-0 items-center gap-1.5 text-xs">
            <span className="bg-primary inline-block size-1.5 shrink-0 rounded-full" aria-hidden />
            <span className="truncate">{rankSubtitle}</span>
          </p>
        ) : (
          <span />
        )}

        {!loading && tag?.type === "rank" ? (
          <Badge variant="muted" className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold">
            #{tag.rank}
          </Badge>
        ) : null}
        {!loading && tag?.type === "improve" ? (
          <Badge variant="orange" className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold">
            可提升
          </Badge>
        ) : null}
      </div>
    </div>
  );
}
