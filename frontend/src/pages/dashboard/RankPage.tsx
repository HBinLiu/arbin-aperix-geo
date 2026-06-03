import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchRank } from "@/api/analysis";
import { defaultDateRange, formatRate } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import { cn } from "@/lib/utils";

type RankContentProps = {
  subjectId: string;
};

/** 竞品声量排行榜。 */
export function RankContent({ subjectId }: RankContentProps) {
  const { from, to } = useMemo(() => defaultDateRange(), []);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.rank(subjectId, from, to),
    queryFn: () => fetchRank(subjectId, from, to),
  });

  if (isLoading) {
    return (
      <div className="px-4 py-6 sm:px-5">
        <div className="bg-muted h-64 animate-pulse rounded-lg" />
      </div>
    );
  }

  if (!data || data.response_count === 0) {
    return (
      <div className="text-muted-foreground px-4 py-12 text-center text-sm sm:px-5">
        暂无采样数据，请等待诊断流水线完成。
      </div>
    );
  }

  const labels = Object.keys(data.share_of_voice).sort((a, b) => {
    return (data.share_of_voice[b] ?? 0) - (data.share_of_voice[a] ?? 0);
  });
  const maxShare = Math.max(...labels.map((l) => data.share_of_voice[l] ?? 0), 0.01);

  return (
    <div className="flex h-full flex-col px-4 py-3 sm:px-5">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight">竞品声量排行</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          基于提及次数的声量份额（近 30 天，{data.response_count} 条回复）
        </p>
      </div>

      <div className="border-border overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
            <tr>
              <th className="px-4 py-2.5 font-medium">实体</th>
              <th className="px-4 py-2.5 font-medium">提及次数</th>
              <th className="px-4 py-2.5 font-medium">可见度份额</th>
              <th className="px-4 py-2.5 font-medium">声量份额</th>
            </tr>
          </thead>
          <tbody>
            {labels.map((label) => {
              const isOwn = label === data.own_label;
              const voiceShare = data.share_of_voice[label] ?? 0;
              return (
                <tr key={label} className="border-border border-t">
                  <td className="px-4 py-3">
                    <span className={cn("font-medium", isOwn && "text-primary")}>
                      {label}
                      {isOwn ? "（自有）" : ""}
                    </span>
                  </td>
                  <td className="px-4 py-3 tabular-nums">{data.mention_counts[label] ?? 0}</td>
                  <td className="px-4 py-3 tabular-nums">
                    {formatRate(data.visibility_share[label] ?? 0)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="bg-muted h-2 flex-1 overflow-hidden rounded-full">
                        <div
                          className={cn("h-full rounded-full", isOwn ? "bg-primary" : "bg-foreground/40")}
                          style={{ width: `${(voiceShare / maxShare) * 100}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-xs tabular-nums">
                        {formatRate(voiceShare)}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
