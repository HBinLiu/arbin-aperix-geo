import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRate } from "@/lib/analysis/format";
import { citationDomainDetailPath } from "@/lib/analysis/nav";
import type { CitationDomainRow } from "@/types";

const SKELETON_ROWS = 8;
const TABLE_MIN_HEIGHT = 420;
const COLUMN_COUNT = 4;
const COL_DOMAIN_WIDTH = "32%";
const COL_TYPE_WIDTH = "28%";
const COL_COUNT_WIDTH = "20%";
const COL_RATE_WIDTH = "20%";

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
  const navigate = useNavigate();
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
                <span className="inline-flex items-center gap-1">
                  数量
                  <ColumnHelp label="数量" description="该此域名被引用为来源的 AI 生成答案总数。" />
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
                      <FaviconImage domain={row.host} size={20} className="size-5 shrink-0 rounded-sm" />
                      <span
                        className="truncate font-medium hover:text-primary hover:underline"
                        title={row.host}
                      >
                        {row.host}
                      </span>
                    </div>
                  </td>
                  <td className="px-4">
                    <Badge variant="grayBlack" className="px-2 py-1 font-semibold">
                      {row.domain_type ?? "其它类型"}
                    </Badge>
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
