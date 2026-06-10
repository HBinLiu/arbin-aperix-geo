import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { CitationUrlPromptsDialog } from "@/components/analysis/citation/CitationUrlPromptsDialog";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { citationMentionsOwnBrand } from "@/lib/analysis/citation";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";
import type { CitationMentionedBrand, CitationUrlRow } from "@/types";

const SKELETON_ROWS = 8;
const TABLE_MIN_HEIGHT = 420;
const COLUMN_COUNT = 6;
const MENTIONED_BRAND_VISIBLE_LIMIT = 5;
const URL_COUNT_DESCRIPTION = "此特定页面在 AI 生成答案中被引用为来源的总次数。";
const URL_CITATION_RATE_DESCRIPTION = "此特定页面在此域名总引用量中的占比。";

type UrlSortKey = "count" | "citation_rate";
type UrlSortDir = "asc" | "desc";
type UrlSortState = { key: UrlSortKey; dir: UrlSortDir } | null;

function cycleUrlSort(prev: UrlSortState, key: UrlSortKey): UrlSortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

function compareUrlRows(a: CitationUrlRow, b: CitationUrlRow, sort: UrlSortState): number {
  if (!sort) {
    return b.count - a.count;
  }

  const diff =
    sort.key === "count" ? a.count - b.count : a.citation_rate - b.citation_rate;
  if (diff === 0) return a.url.localeCompare(b.url);
  return sort.dir === "asc" ? diff : -diff;
}

type UrlSortableHeaderProps = {
  label: string;
  sortKey: UrlSortKey;
  sort: UrlSortState;
  onSort: (key: UrlSortKey) => void;
  help: { label: string; description: string };
};

function UrlSortableHeader({ label, sortKey, sort, onSort, help }: UrlSortableHeaderProps) {
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
    <span className="inline-flex items-center gap-1">
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
      <ColumnHelp label={help.label} description={help.description} />
    </span>
  );
}

function brandFaviconTarget(brand: CitationMentionedBrand): string {
  return brand.domain ?? brand.label;
}

function brandDisplayDomain(brand: CitationMentionedBrand): string {
  return brand.domain ?? brand.label;
}

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
    <div className="flex min-w-0 items-center gap-2.5 text-left">
      <FaviconImage domain={displayHost} pageUrl={url} size={20} className="size-5 shrink-0 rounded-sm" />
      <div className="min-w-0 text-left">
        <p className="truncate text-left font-medium text-foreground">{title}</p>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground block truncate text-left text-sm hover:underline"
          onClick={(event) => event.stopPropagation()}
        >
          {url}
        </a>
      </div>
    </div>
  );
}

function MentionStatusCell({ mentioned }: { mentioned: boolean | null }) {
  if (mentioned == null) {
    return <span className="text-[10px] font-bold text-muted-foreground">—</span>;
  }

  return (
    <Badge variant={mentioned ? "success" : "error"} className="px-1.5 py-0.5 font-semibold">
      <span
        className={cn("size-2 shrink-0 rounded-full", mentioned ? "bg-success" : "bg-error")}
        aria-hidden
      />
      {mentioned ? "是" : "否"}
    </Badge>
  );
}

function MentionedBrandsCell({ brands }: { brands: CitationMentionedBrand[] }) {
  if (brands.length === 0) {
    return <span className="text-[10px] font-bold text-muted-foreground">—</span>;
  }

  const visible = brands.slice(0, MENTIONED_BRAND_VISIBLE_LIMIT);
  const overflow = brands.length - visible.length;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className="inline-flex cursor-default items-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          tabIndex={0}
          role="img"
          aria-label={`${brands.length} 个提及品牌`}
          onClick={(event) => event.stopPropagation()}
        >
          <span className="flex items-center -space-x-1">
            {visible.map((brand, index) => (
              <span
                key={`${brand.label}-${brand.domain ?? index}`}
                className="ring-background inline-flex rounded-full ring-2"
              >
                <BrandRankIcon label={brandFaviconTarget(brand)} size="sm" shape="circle" />
              </span>
            ))}
          </span>
          {overflow > 0 ? (
            <span className="text-muted-foreground ml-1 shrink-0 text-xs tabular-nums">
              +{overflow}
            </span>
          ) : null}
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        showArrow={false}
        className="border-border w-auto min-w-48 border bg-white px-3 py-2.5 text-foreground shadow-lg"
      >
        <ul className="flex flex-col gap-2">
          {brands.map((brand, index) => (
            <li
              key={`${brand.label}-${brand.domain ?? index}`}
              className="flex items-center gap-2"
            >
              <BrandRankIcon label={brandFaviconTarget(brand)} size="sm" shape="circle" />
              <span className="text-sm font-normal">{brandDisplayDomain(brand)}</span>
            </li>
          ))}
        </ul>
      </TooltipContent>
    </Tooltip>
  );
}

export function CitationUrlTable({ rows, ownLabel, ownBrand, loading = false }: CitationUrlTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<UrlSortState>(null);
  const [selectedRow, setSelectedRow] = useState<CitationUrlRow | null>(null);
  const [promptsOpen, setPromptsOpen] = useState(false);

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => compareUrlRows(a, b, sort)),
    [rows, sort],
  );
  const pageRows = useMemo(
    () => paginateRows(sortedRows, page, pageSize),
    [sortedRows, page, pageSize],
  );

  useEffect(() => {
    setPage(1);
  }, [sort]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  const openPromptsDialog = (row: CitationUrlRow) => {
    setSelectedRow(row);
    setPromptsOpen(true);
  };

  return (
    <>
      <CitationUrlPromptsDialog
        row={selectedRow}
        open={promptsOpen}
        onOpenChange={setPromptsOpen}
      />
      <div
      className="border-border overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="overflow-x-auto" style={{ minHeight: TABLE_MIN_HEIGHT }}>
        <table className="w-full min-w-[960px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: "35%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5 pr-10">URL</th>
              <th>
                <span className="inline-flex items-center gap-1">
                  URL 类型
                  <ColumnHelp
                    label="URL 类型"
                    description="对 AI 引用的页面内容类型进行分类。反映算法偏好的内容结构。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  是否提及
                  <ColumnHelp
                    label="是否提及"
                    description="AI 回复中直接提及的品牌。用于衡量此特定页面的竞争表现。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  提及品牌
                  <ColumnHelp
                    label="提及品牌"
                    description="AI 回复中直接提及的品牌。用于衡量此特定页面的竞争表现。"
                  />
                </span>
              </th>
              <th>
                <UrlSortableHeader
                  label="数量"
                  sortKey="count"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleUrlSort(prev, key))}
                  help={{ label: "数量", description: URL_COUNT_DESCRIPTION }}
                />
              </th>
              <th>
                <UrlSortableHeader
                  label="引用率"
                  sortKey="citation_rate"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleUrlSort(prev, key))}
                  help={{ label: "引用率", description: URL_CITATION_RATE_DESCRIPTION }}
                />
              </th>
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
                <tr
                  key={row.url}
                  className="border-border hover:bg-muted/40 cursor-pointer border-t [&>td]:py-3"
                  onClick={() => openPromptsDialog(row)}
                >
                  <td className="max-w-0 pl-5 pr-10">
                    <UrlCell url={row.url} host={row.host} title={row.title || row.url} />
                  </td>
                  <td className="px-4">
                    <Badge variant="grayBlack" className="px-2 py-1 font-semibold">
                      {row.url_type ?? "其它类型"}
                    </Badge>
                  </td>
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
                  <td className="px-4 font-semibold tabular-nums">{row.count}</td>
                  <td className="px-4 font-semibold tabular-nums">
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
    </>
  );
}
