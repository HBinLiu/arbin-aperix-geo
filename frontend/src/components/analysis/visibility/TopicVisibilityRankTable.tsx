import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { CompetitorHoverCard } from "@/components/brand/CompetitorHoverCard";
import { LabelHoverPortal } from "@/components/brand/LabelHoverPortal";
import { Skeleton } from "@/components/ui/skeleton";
import { useBrandHoverRow } from "@/hooks/useBrandHoverRow";
import { cn } from "@/lib/utils";

export type TopicVisibilityRankRow = {
  topicId: string;
  topicName: string;
  ranks: (string | null)[];
};

const RANK_SLOTS = ["#1", "#2", "#3", "#4", "#5"] as const;
const TOPIC_COLUMN_WIDTH = "30%";
const RANK_COLUMN_WIDTH = "14%";
const SKELETON_GRID_COLUMNS = `${TOPIC_COLUMN_WIDTH} ${RANK_SLOTS.map(() => RANK_COLUMN_WIDTH).join(" ")}`;
const HOVER_CARD_ANIMATION =
  "animate-in fade-in-0 zoom-in-95 slide-in-from-left-2 duration-200";

function TopicRankBrandIcon({ label }: { label: string }) {
  const resolvedHoverRow = useBrandHoverRow(label);

  return (
    <LabelHoverPortal
      label={label}
      className="inline-flex shrink-0"
      trigger={<BrandRankIcon label={label} />}
      content={<CompetitorHoverCard row={resolvedHoverRow} />}
      contentClassName={HOVER_CARD_ANIMATION}
    />
  );
}

type TopicVisibilityRankTableProps = {
  rows: TopicVisibilityRankRow[];
  ownLabel?: string;
  loading?: boolean;
  className?: string;
};

function TopicVisibilityRankSkeleton() {
  return (
    <div className="space-y-0" aria-hidden>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="border-border grid items-center border-t py-3"
          style={{ gridTemplateColumns: SKELETON_GRID_COLUMNS }}
        >
          <div className="pl-5 pr-4">
            <Skeleton className="h-4 w-3/4" />
          </div>
          {RANK_SLOTS.map((slot) => (
            <div key={slot} className="flex justify-center px-4">
              <Skeleton className="size-7 rounded-md" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/** 主题可见度排名：每行主题 + Top5 品牌图标 */
export function TopicVisibilityRankTable({
  rows,
  ownLabel = "",
  loading = false,
  className,
}: TopicVisibilityRankTableProps) {
  return (
    <section
      className={cn(
        "border-border overflow-hidden rounded-lg border bg-white",
        className,
      )}
      aria-busy={loading}
    >
      <div className="border-border border-b px-5 py-4">
        <h3 className="text-base font-semibold">主题可见度排名</h3>
        <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
          快速洞察竞争格局，围绕话题与场景识别品牌表现与竞争机会。
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: TOPIC_COLUMN_WIDTH }} />
            {RANK_SLOTS.map((slot) => (
              <col key={slot} style={{ width: RANK_COLUMN_WIDTH }} />
            ))}
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:align-middle [&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-3 [&>th]:font-medium">
              <th className="pl-5">主题</th>
              {RANK_SLOTS.map((slot) => (
                <th key={slot} className="text-center">
                  {slot}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={RANK_SLOTS.length + 1} className="p-0">
                  <TopicVisibilityRankSkeleton />
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={RANK_SLOTS.length + 1} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无主题排名数据
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.topicId}
                  className="border-border border-t [&>td]:align-middle [&>td]:whitespace-nowrap [&>td]:px-4 [&>td]:py-3"
                >
                  <td className="text-foreground pl-5 font-medium">
                    <span className="inline-flex items-center gap-1.5">
                      <span>{row.topicName}</span>
                      {ownLabel && row.ranks[0] === ownLabel ? (
                        <span className="inline-flex shrink-0 items-center rounded-full bg-primary px-2 py-0.5 text-xs font-bold text-white">
                          领先
                        </span>
                      ) : null}
                    </span>
                  </td>
                  {RANK_SLOTS.map((slot, index) => (
                    <td key={slot} className="text-center">
                      <div className="flex h-7 items-center justify-center">
                        {row.ranks[index] ? (
                          <TopicRankBrandIcon label={row.ranks[index]!} />
                        ) : (
                          <BrandRankIcon label={null} />
                        )}
                      </div>
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
