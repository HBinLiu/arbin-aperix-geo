import { useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRate } from "@/lib/analysis/format";
import type { CitationDomainRow } from "@/types";

const SKELETON_ROWS = 8;
const TABLE_MIN_HEIGHT = 420;
const COLUMN_COUNT = 4;

type CitationDomainTableProps = {
  rows: CitationDomainRow[];
  loading?: boolean;
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

export function CitationDomainTable({ rows, loading = false }: CitationDomainTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const pageRows = useMemo(() => paginateRows(rows, page, pageSize), [rows, page, pageSize]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  return (
    <div
      className="border-border overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="overflow-x-auto" style={{ minHeight: TABLE_MIN_HEIGHT }}>
        <table className="w-full min-w-[720px] table-auto text-sm">
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">域名</th>
              <th>
                <span className="inline-flex items-center gap-1">
                  域名类型
                  <ColumnHelp
                    label="域名类型"
                    description="域名所属类型分类，暂无数据时显示 —。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  数量
                  <ColumnHelp label="数量" description="该域名在 AI 回复中被引用的次数。" />
                </span>
              </th>
              <th>引用率</th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {loading ? (
              <SkeletonRows />
            ) : rows.length === 0 ? (
              <tr>
                <td
                  colSpan={COLUMN_COUNT}
                  className="text-muted-foreground px-4 text-center align-middle"
                  style={{ height: TABLE_MIN_HEIGHT - 40 }}
                >
                  暂无域名数据
                </td>
              </tr>
            ) : (
              pageRows.map((row) => (
                <tr key={row.host} className="border-border border-t [&>td]:py-3">
                  <td className="pl-5">
                    <div className="flex items-center gap-2 whitespace-nowrap">
                      <FaviconImage domain={row.host} size={20} className="size-5 rounded-sm" />
                      <span className="font-medium">{row.host}</span>
                    </div>
                  </td>
                  <td className="px-4">{row.domain_type ?? "—"}</td>
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

      {!loading && rows.length > 0 ? (
        <TablePagination
          total={rows.length}
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
