import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacklinkOpportunityPrompts } from "@/hooks/useBacklinkOpportunityDetail";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";
import type { AnalysisFilters, CitationDomainPromptSortField, SamplingPlatform } from "@/types";

const SKELETON_ROWS = 8;
const COLUMN_COUNT = 5;

type SortKey = CitationDomainPromptSortField;
type SortDir = "asc" | "desc";
type SortState = { key: SortKey; dir: SortDir } | null;

function cycleSort(prev: SortState, key: SortKey): SortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

function sortParams(sort: SortState): { sortBy: CitationDomainPromptSortField; order: "asc" | "desc" } {
  if (!sort) {
    return { sortBy: "count", order: "desc" };
  }
  return { sortBy: sort.key, order: sort.dir };
}

type SortableHeaderProps = {
  label: string;
  sortKey: SortKey;
  sort: SortState;
  onSort: (key: SortKey) => void;
};

function SortableHeader({ label, sortKey, sort, onSort }: SortableHeaderProps) {
  const active = sort?.key === sortKey;
  const dir = active ? sort.dir : null;

  const icon =
    dir === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : dir === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-0.5 transition-colors",
        active ? "text-primary" : "text-muted-foreground",
      )}
      aria-label={`按${label}排序`}
      aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}
      onClick={() => onSort(sortKey)}
    >
      {label}
      {icon}
    </button>
  );
}

type OpportunityBacklinkPromptTableProps = {
  subjectId: string;
  host: string;
  filters: AnalysisFilters;
  platformsMeta: SamplingPlatform[];
};

export function OpportunityBacklinkPromptTable({
  subjectId,
  host,
  filters,
  platformsMeta,
}: OpportunityBacklinkPromptTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<SortState>(null);
  const { sortBy, order } = sortParams(sort);

  const { rows, total, isLoading } = useBacklinkOpportunityPrompts(subjectId, filters, {
    host,
    page,
    pageSize,
    sortBy,
    order,
  });

  useEffect(() => {
    setPage(1);
  }, [sort, pageSize, host, filters]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  return (
    <div className="border-border overflow-hidden rounded-lg border bg-white" aria-busy={isLoading}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: "32%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "20%" }} />
            <col style={{ width: "15%" }} />
            <col style={{ width: "15%" }} />
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">提示词</th>
              <th>主题</th>
              <th>平台</th>
              <th>
                <SortableHeader
                  label="引用次数"
                  sortKey="count"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                />
              </th>
              <th>
                <SortableHeader
                  label="引用率"
                  sortKey="citation_rate"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                />
              </th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {isLoading ? (
              Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
                <tr key={rowIndex} className="border-border border-t [&>td]:py-3" aria-hidden>
                  {Array.from({ length: COLUMN_COUNT }).map((__, cellIndex) => (
                    <td key={cellIndex} className={cellIndex === 0 ? "pl-5" : "px-4"}>
                      <Skeleton className="h-4 w-4/5" />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无提示词数据
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-border border-t [&>td]:py-3">
                  <td className="max-w-0 pl-5">
                    <span className="block truncate font-medium">{row.name}</span>
                  </td>
                  <td className="px-4 text-muted-foreground truncate">{row.topic_name ?? "—"}</td>
                  <td className="px-4">
                    <PlatformLogoGroup
                      providers={row.platforms ?? []}
                      platforms={platformsMeta}
                      logoClassName="size-5"
                    />
                  </td>
                  <td className="px-4 font-semibold tabular-nums">{row.count}</td>
                  <td className="px-4 font-semibold tabular-nums">{formatRate(row.citation_rate)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!isLoading && total > 0 ? (
        <TablePagination
          total={total}
          page={page}
          pageSize={pageSize}
          pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
          onPageChange={setPage}
          onPageSizeChange={handlePageSizeChange}
        />
      ) : null}
    </div>
  );
}
