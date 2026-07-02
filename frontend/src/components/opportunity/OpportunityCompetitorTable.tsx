import {
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Loader2,
  UserPlus,
} from "lucide-react";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  EmptyMetricCell,
  SentimentMetricCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { rankBoardRowToBrandGeoMetrics } from "@/lib/brand/geoMetrics";
import {
  BRAND_COLUMNS,
  BRAND_MIN_WIDTH,
  type BrandRow,
  type BrandSortColumn,
} from "@/lib/opportunity/brand";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

export type BrandSortState = {
  column: BrandSortColumn;
  dir: HeaderMode;
};

export const DEFAULT_BRAND_SORT: BrandSortState = {
  column: "visibility",
  dir: "desc",
};

type SortableHeaderProps = {
  column: BrandSortColumn;
  label: string;
  sort: BrandSortState;
  onSort: (column: BrandSortColumn) => void;
};

function cycleSort(state: BrandSortState, column: BrandSortColumn): BrandSortState {
  if (state.column !== column || state.dir === "default") {
    const col = BRAND_COLUMNS.find((item) => item.id === column)!;
    return { column, dir: col.higherIsBetter ? "desc" : "asc" };
  }
  if (state.dir === "desc") return { column, dir: "asc" };
  return { column, dir: "default" };
}

function SortableHeader({ column, label, sort, onSort }: SortableHeaderProps) {
  const isActive = sort.column === column && sort.dir !== "default";
  const mode = sort.column === column ? sort.dir : "default";

  const sortIcon =
    mode === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : mode === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-0.5 whitespace-nowrap transition-colors",
        isActive ? "text-primary" : "text-muted-foreground",
      )}
      aria-label={`按${label}排序`}
      aria-sort={mode === "asc" ? "ascending" : mode === "desc" ? "descending" : "none"}
      onClick={() => onSort(column)}
    >
      <span>{label}</span>
      {sortIcon}
    </button>
  );
}

function CompetitorSkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          <td className="tabular-nums pl-5">
            <Skeleton className="h-4 w-5" />
          </td>
          <td>
            <Skeleton className="h-4 w-28" />
          </td>
          {BRAND_COLUMNS.map((column) => (
            <td key={column.id}>
              <Skeleton className="h-4 w-16" />
            </td>
          ))}
          <td>
            <Skeleton className="h-8 w-24" />
          </td>
        </tr>
      ))}
    </>
  );
}

type OpportunityCompetitorTableProps = {
  rows: BrandRow[];
  loading?: boolean;
  fetching?: boolean;
  total: number;
  page: number;
  pageSize: number;
  sort: BrandSortState;
  onSortChange: (sort: BrandSortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  promotingBrandId?: string | null;
  onPromote?: (target: { brandId: string; label: string }) => void;
};

export function OpportunityCompetitorTable({
  rows,
  loading = false,
  fetching = false,
  total,
  page,
  pageSize,
  sort,
  onSortChange,
  onPageChange,
  onPageSizeChange,
  promotingBrandId = null,
  onPromote,
}: OpportunityCompetitorTableProps) {
  const activeColumn = sort.dir === "default" ? null : sort.column;

  const handleSort = (column: BrandSortColumn) => {
    onSortChange(cycleSort(sort, column));
  };

  const handlePageSizeChange = (next: number) => {
    onPageSizeChange(next);
    onPageChange(1);
  };

  return (
    <PerformanceTableShell
      loading={fetching}
      scrollMinWidth={BRAND_MIN_WIDTH}
      footer={
        total > 0 ? (
          <TablePagination
            total={total}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={onPageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          <col style={{ width: "3%" }} />
          <col style={{ width: "20%" }} />
          {BRAND_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
          <col style={{ width: "12%" }} />
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">#</th>
            <th>品牌</th>
            {BRAND_COLUMNS.map((column) => (
              <th key={column.id}>
                <SortableHeader
                  column={column.id}
                  label={column.label}
                  sort={sort}
                  onSort={handleSort}
                />
              </th>
            ))}
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            <CompetitorSkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td
                colSpan={BRAND_COLUMNS.length + 3}
                className="text-muted-foreground px-5 py-10 text-center text-sm"
              >
                暂无潜在竞品
              </td>
            </tr>
          ) : (
            rows.map((row, index) => {
              const isPromoting = promotingBrandId === row.brandId;
              return (
                <tr key={row.brandId} className={performanceTableClasses.row}>
                  <td className="text-foreground pl-5 tabular-nums">#{(page - 1) * pageSize + index + 1}</td>
                  <td className="min-w-0 overflow-hidden px-4 whitespace-normal">
                    <BrandRankLabel
                      label={row.label}
                      domain={row.domain}
                      isOwn={false}
                      geoMetrics={rankBoardRowToBrandGeoMetrics({
                        id: row.brandId,
                        label: row.label,
                        domain: row.domain,
                        isOwn: false,
                        visibility: row.visibility,
                        visibilityNum: 0,
                        shareVoice: row.shareVoice,
                        shareVoiceNum: null,
                        mention: row.mention,
                        mentionNum: 0,
                        averageRank: row.averageRank,
                        averageRankNum: null,
                        citationRate: row.citationRate,
                        citationNum: 0,
                        sentiment: row.sentiment,
                        sentimentNum: null,
                        sentimentLabel: row.sentimentLabel,
                      })}
                    />
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "visibility" && "text-primary")}>
                    {row.visibility}
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "shareVoice" && "text-primary")}>
                    {row.shareVoice === "—" ? <EmptyMetricCell /> : row.shareVoice}
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "mention" && "text-primary")}>
                    {row.mention}
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "averageRank" && "text-primary")}>
                    {row.averageRank === "—" ? <EmptyMetricCell /> : row.averageRank}
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "citation" && "text-primary")}>
                    {row.citationRate}
                  </td>
                  <td className={cn("font-medium tabular-nums", activeColumn === "sentiment" && "text-primary")}>
                    <SentimentMetricCell value={row.sentiment} label={row.sentimentLabel} />
                  </td>
                  <td>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1.5 text-xs"
                      disabled={!onPromote || isPromoting}
                      onClick={() => onPromote?.({ brandId: row.brandId, label: row.label })}
                    >
                      {isPromoting ? (
                        <Loader2 className="size-3.5 animate-spin" aria-hidden />
                      ) : (
                        <UserPlus className="size-3.5" aria-hidden />
                      )}
                      添加为竞品
                    </Button>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
