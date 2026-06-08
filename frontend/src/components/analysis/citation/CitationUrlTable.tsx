import { useMemo, useState } from "react";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Skeleton } from "@/components/ui/skeleton";
import { citationMentionsOwnBrand } from "@/lib/analysis/citation";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";
import type { CitationMentionedBrand, CitationUrlRow } from "@/types";

const SKELETON_ROWS = 8;
const TABLE_MIN_HEIGHT = 420;
const COLUMN_COUNT = 6;
const MENTIONED_BRAND_LIMIT = 3;

type CitationUrlTableProps = {
  rows: CitationUrlRow[];
  ownLabel: string;
  ownBrand?: string | null;
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

function UrlCell({ url, host, title }: { url: string; host: string; title: string }) {
  const displayHost = host || url;

  return (
    <div className="flex min-w-0 items-start gap-2.5">
      <FaviconImage domain={displayHost} size={20} className="mt-0.5 size-5 shrink-0 rounded-sm" />
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{title}</p>
        <p className="text-muted-foreground truncate text-xs">{url}</p>
      </div>
    </div>
  );
}

function MentionStatusCell({ mentioned }: { mentioned: boolean | null }) {
  if (mentioned == null) {
    return <span className="text-muted-foreground">—</span>;
  }

  return (
    <div className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        className={cn(
          "inline-block size-2 rounded-full",
          mentioned ? "bg-emerald-500" : "bg-red-500",
        )}
        aria-hidden
      />
      <span>{mentioned ? "是" : "否"}</span>
    </div>
  );
}

function MentionedBrandsCell({ brands }: { brands: CitationMentionedBrand[] }) {
  if (brands.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const visible = brands.slice(0, MENTIONED_BRAND_LIMIT);
  const overflow = brands.length - visible.length;

  return (
    <div className="flex items-center">
      <div className="flex items-center -space-x-1">
        {visible.map((brand) => (
          <BrandRankIcon
            key={brand.label}
            label={brand.domain ?? brand.label}
            size="sm"
          />
        ))}
      </div>
      {overflow > 0 ? (
        <span className="bg-muted text-muted-foreground ml-1 inline-flex size-5 shrink-0 items-center justify-center rounded-md text-[10px] font-medium tabular-nums">
          +{overflow}
        </span>
      ) : null}
    </div>
  );
}

export function CitationUrlTable({ rows, ownLabel, ownBrand, loading = false }: CitationUrlTableProps) {
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
        <table className="w-full min-w-[960px] table-auto text-sm">
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="min-w-[280px] pl-5">URL</th>
              <th>
                <span className="inline-flex items-center gap-1">
                  URL 类型
                  <ColumnHelp
                    label="URL 类型"
                    description="引用页内容类型推断结果，暂无数据时显示 —。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  是否提及
                  <ColumnHelp
                    label="是否提及"
                        description="根据 LLM 提取的提及品牌列表，判断是否包含本品牌；无分析数据时显示 —。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  提及品牌
                  <ColumnHelp
                    label="提及品牌"
                    description="来源页正文中检测到的竞品品牌。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  数量
                  <ColumnHelp label="数量" description="该 URL 在 AI 回复中被引用的次数。" />
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
                  暂无 URL 数据
                </td>
              </tr>
            ) : (
              pageRows.map((row) => (
                <tr key={row.url} className="border-border border-t [&>td]:py-3">
                  <td className="max-w-[420px] pl-5">
                    <UrlCell url={row.url} host={row.host} title={row.title || row.url} />
                  </td>
                  <td className="px-4 whitespace-nowrap">{row.url_type ?? "—"}</td>
                  <td className="px-4">
                    <MentionStatusCell
                      mentioned={citationMentionsOwnBrand(
                        row.mentioned_brands,
                        ownLabel,
                        ownBrand,
                        row.has_brand_analysis,
                      )}
                    />
                  </td>
                  <td className="px-4">
                    <MentionedBrandsCell brands={row.mentioned_brands} />
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
