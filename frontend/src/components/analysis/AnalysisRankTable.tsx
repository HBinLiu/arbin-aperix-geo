import { ChevronDown } from "lucide-react";

import { LabelBadge } from "@/components/common/LabelBadge";
import { cn } from "@/lib/utils";

export type RankRow = {
  id: string;
  label: string;
  value: string;
  delta: string | null;
  isOwn?: boolean;
  icon?: React.ReactNode;
};

const DEFAULT_HEIGHT_CLASS = "max-h-[400px]";

type AnalysisRankTableProps = {
  title: string;
  valueHeader: string;
  rows: RankRow[];
  emptyMessage?: string;
  embedded?: boolean;
  showMoreFooter?: boolean;
  className?: string;
};

export function AnalysisRankTable({
  title,
  valueHeader,
  rows,
  emptyMessage = "暂无排名数据",
  embedded = false,
  showMoreFooter = false,
  className,
}: AnalysisRankTableProps) {
  if (rows.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col",
          DEFAULT_HEIGHT_CLASS,
          embedded ? "bg-transparent" : "border-border bg-card rounded-lg border p-4",
          className,
        )}
      >
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="flex flex-1 items-center justify-center">
          <p className="text-muted-foreground text-sm">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden",
        DEFAULT_HEIGHT_CLASS,
        embedded ? "bg-transparent" : "border-border bg-card rounded-lg border",
        className,
      )}
    >
      <div className={cn("shrink-0 px-4 py-3", !embedded && "border-border border-b")}>
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <table className="w-max min-w-full table-auto text-sm">
          <thead className="text-muted-foreground text-left text-xs">
            <tr className="[&>th]:py-2">
              <th className="w-10 min-w-10 max-w-10 px-2 pl-4 font-medium">#</th>
              <th className="min-w-[5rem] px-4 font-medium">品牌</th>
              <th className="min-w-[3.5rem] whitespace-nowrap px-4 font-medium">
                <span className="inline-flex items-center gap-0.5">
                  {valueHeader}
                  <ChevronDown className="size-3 shrink-0" aria-hidden />
                </span>
              </th>
              <th className="min-w-[2.75rem] whitespace-nowrap px-4 font-medium">趋势</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.id} className="border-border border-t [&>td]:py-2">
                <td className="text-foreground w-10 min-w-10 max-w-10 px-2 pl-4 tabular-nums">
                  #{index + 1}
                </td>
                <td className="min-w-[5rem] px-4">
                  <div className="flex items-center gap-2">
                    {row.icon ? (
                      <span className="inline-flex size-6 shrink-0 items-center justify-center [&_img]:size-6">
                        {row.icon}
                      </span>
                    ) : (
                      <span className="bg-muted text-muted-foreground flex size-6 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
                        {row.label.slice(0, 1).toUpperCase()}
                      </span>
                    )}
                    <span className="whitespace-nowrap font-medium">{row.label}</span>
                    {row.isOwn ? <LabelBadge variant="orange" className="shrink-0">拥有</LabelBadge> : null}
                  </div>
                </td>
                <td className="min-w-[3.5rem] whitespace-nowrap px-4 font-medium tabular-nums">
                  {row.value}
                </td>
                <td className="min-w-[2.75rem] whitespace-nowrap px-4 tabular-nums">
                  {row.delta ? (
                    <span
                      className={cn(
                        "text-xs font-medium tabular-nums",
                        row.delta.startsWith("+")
                          ? "text-emerald-600"
                          : row.delta.startsWith("-")
                            ? "text-red-600"
                            : "text-muted-foreground",
                      )}
                    >
                      {row.delta}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showMoreFooter && rows.length > 0 ? (
        <div className="shrink-0 px-4 py-2">
          <button
            type="button"
            className="border-border text-foreground w-full rounded-lg border py-2 text-center text-sm font-semibold transition-colors"
          >
            更多
          </button>
        </div>
      ) : null}
    </div>
  );
}
