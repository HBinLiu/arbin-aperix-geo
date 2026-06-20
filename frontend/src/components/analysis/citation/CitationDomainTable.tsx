import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { faviconUrlFromHost } from "@/lib/favicon";
import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCitationDomains } from "@/hooks/useCitationList";
import { formatRate } from "@/lib/analysis/format";
import { citationDomainDetailPath } from "@/lib/analysis/nav";
import { cn } from "@/lib/utils";
import type { AnalysisFilters, CitationDomainSortField } from "@/types";

const SKELETON_ROWS = 8;
const COLUMN_COUNT = 4;
const COL_DOMAIN_WIDTH = "32%";
const COL_TYPE_WIDTH = "28%";
const COL_COUNT_WIDTH = "20%";
const COL_RATE_WIDTH = "20%";

type DomainSortDir = "asc" | "desc";
type DomainSortState = DomainSortDir | null;

function cycleDomainSort(prev: DomainSortState): DomainSortState {
  if (prev === null) return "desc";
  if (prev === "desc") return "asc";
  return null;
}

function domainSortParams(sort: DomainSortState): {
  sortBy: CitationDomainSortField;
  order: "asc" | "desc";
} {
  return { sortBy: "count", order: sort ?? "desc" };
}

type DomainSortableHeaderProps = {
  label: string;
  sort: DomainSortState;
  onSort: () => void;
  help: { label: string; description: string };
};

function DomainSortableHeader({ label, sort, onSort, help }: DomainSortableHeaderProps) {
  const icon =
    sort === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : sort === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-0.5 transition-colors",
          sort ? "text-primary" : "text-muted-foreground",
        )}
        aria-label={`按${label}排序`}
        aria-sort={sort === "asc" ? "ascending" : sort === "desc" ? "descending" : "none"}
        onClick={onSort}
      >
        {label}
        {icon}
      </button>
      <ColumnHelp label={help.label} description={help.description} />
    </span>
  );
}

type CitationDomainTableProps = {
  subjectId: string;
  filters: AnalysisFilters;
  citationSearch?: string;
};

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className="border-border border-t [&>td]:py-3" aria-hidden>
          {Array.from({ length: COLUMN_COUNT }).map((__, cellIndex) => (
            <td key={cellIndex} className={cellIndex === 0 ? "pl-5" : "px-4"}>
              <Skeleton className="h-4 w-4/5" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function CitationDomainTable({
  subjectId,
  filters,
  citationSearch = "",
}: CitationDomainTableProps) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<DomainSortState>(null);
  const { sortBy, order } = domainSortParams(sort);

  const { isLoading, rows, total } = useCitationDomains(subjectId, filters, {
    page,
    pageSize,
    sortBy,
    order,
    search: citationSearch,
  });

  useEffect(() => {
    setPage(1);
  }, [sort, pageSize, filters, citationSearch]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  return (
    <div
      className="border-border overflow-hidden rounded-lg border bg-white"
      aria-busy={isLoading}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: COL_DOMAIN_WIDTH }} />
            <col style={{ width: COL_TYPE_WIDTH }} />
            <col style={{ width: COL_COUNT_WIDTH }} />
            <col style={{ width: COL_RATE_WIDTH }} />
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">域名</th>
              <th>
                <span className="inline-flex items-center gap-1">
                  域名类型
                  <ColumnHelp
                    label="域名类型"
                    description="对 AI 引用的域名来源类型进行分类。帮助识别 AI 算法中不同渠道的权威性差异，从而有针对性地优化您的反向链接策略。"
                  />
                </span>
              </th>
              <th>
                <DomainSortableHeader
                  label="数量"
                  sort={sort}
                  onSort={() => setSort((prev) => cycleDomainSort(prev))}
                  help={{ label: "数量", description: "该此域名被引用为来源的 AI 生成答案总数。" }}
                />
              </th>
              <th>引用率</th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {isLoading ? (
              <SkeletonRows />
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无域名数据
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.host}
                  className="border-border hover:bg-muted/40 cursor-pointer border-t [&>td]:py-3"
                  role="link"
                  tabIndex={0}
                  onClick={() => navigate(citationDomainDetailPath(row.host))}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(citationDomainDetailPath(row.host));
                    }
                  }}
                >
                  <td className="max-w-0 pl-5">
                    <div className="flex min-w-0 items-center gap-2">
                      <FaviconImage url={faviconUrlFromHost(row.host)} size={20} className="size-5 shrink-0 rounded-sm" />
                      <span
                        className="truncate font-medium hover:text-primary hover:underline"
                        title={row.host}
                      >
                        {row.host}
                      </span>
                    </div>
                  </td>
                  <td className="px-4">
                    <TextBadge variant="gray" className="bg-background px-2 py-1 font-semibold text-foreground">
                      {row.domain_type ?? "其它类型"}
                    </TextBadge>
                  </td>
                  <td className="px-4 tabular-nums">{row.count}</td>
                  <td className="px-4 font-medium tabular-nums">
                    {formatRate(row.citation_rate)}
                  </td>
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
