import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PaginatedTableCard } from "@/components/analysis/common/PaginatedTableCard";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import { CitationUrlPromptsDialog } from "@/components/analysis/citation/CitationUrlPromptsDialog";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { wideTableRowClass } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { FaviconImage } from "@/components/common/FaviconImage";
import { DotBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCitationDomainUrls, useCitationUrls } from "@/hooks/useCitationList";
import { DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis/filters";
import { citationMentionsOwnBrand, citationUrlDisplayTitle } from "@/lib/analysis/citation";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";
import type { AnalysisFilters, CitationUrlRow, CitationUrlSortField, SamplingPlatform } from "@/types";

const SKELETON_ROWS = 8;
const COLUMN_COUNT = 6;
const URL_COUNT_DESCRIPTION = "此特定页面在 AI 回复中被引用为来源的总次数。";
const URL_CITATION_RATE_DESCRIPTION = "此特定页面在全部 AI 回复中的引用占比。";

type UrlSortKey = CitationUrlSortField;
type UrlSortDir = "asc" | "desc";
type UrlSortState = { key: UrlSortKey; dir: UrlSortDir } | null;

function cycleUrlSort(prev: UrlSortState, key: UrlSortKey): UrlSortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

function urlSortParams(sort: UrlSortState): { sortBy: CitationUrlSortField; order: "asc" | "desc" } {
  if (!sort) {
    return { sortBy: "count", order: "desc" };
  }
  return { sortBy: sort.key, order: sort.dir };
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

type CitationUrlTableProps = {
  ownLabel: string;
  ownBrand?: string | null;
  citationSearch?: string;
  domain?: string;
} & (
  | {
      subjectId: string;
      filters: AnalysisFilters;
      rows?: never;
      loading?: never;
    }
  | {
      rows: CitationUrlRow[];
      loading?: boolean;
      subjectId?: never;
      filters?: never;
      citationSearch?: never;
      domain?: never;
    }
);

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className={wideTableRowClass} aria-hidden>
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

function UrlCell({ url, title }: { url: string; title: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 text-left">
      <FaviconImage url={url} size={20} className="size-5 shrink-0 rounded-sm" />
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
    <DotBadge variant={mentioned ? "success" : "error"} className="px-1.5 py-0.5 font-semibold">
      {mentioned ? "是" : "否"}
    </DotBadge>
  );
}

export function CitationUrlTable(props: CitationUrlTableProps) {
  const { ownLabel, ownBrand } = props;
  const citationSearch = "citationSearch" in props ? (props.citationSearch ?? "") : "";
  const filterDomain = "domain" in props ? (props.domain ?? "") : "";
  const staticMode = "rows" in props && props.rows != null;
  const domainMode = !staticMode && Boolean(filterDomain);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<UrlSortState>(null);
  const [selectedRow, setSelectedRow] = useState<CitationUrlRow | null>(null);
  const [promptsOpen, setPromptsOpen] = useState(false);
  const { sortBy, order } = urlSortParams(sort);

  const globalQuery = useCitationUrls(
    staticMode || domainMode ? "" : props.subjectId,
    staticMode || domainMode ? DEFAULT_ANALYSIS_FILTERS : props.filters,
    {
      page,
      pageSize,
      sortBy,
      order,
      search: citationSearch,
      enabled: !staticMode && !domainMode,
    },
  );

  const domainQuery = useCitationDomainUrls(
    staticMode || !domainMode ? "" : props.subjectId,
    staticMode || !domainMode ? DEFAULT_ANALYSIS_FILTERS : props.filters,
    {
      domain: filterDomain,
      page,
      pageSize,
      sortBy,
      order,
      enabled: domainMode,
    },
  );

  const remoteQuery = domainMode ? domainQuery : globalQuery;

  const staticRowsSource = staticMode ? props.rows : null;
  const remoteFilters = staticMode ? null : props.filters;

  const staticRows = useMemo(() => {
    if (!staticRowsSource) return [];
    return [...staticRowsSource].sort((a, b) => compareUrlRows(a, b, sort));
  }, [staticRowsSource, sort]);

  const staticPageRows = useMemo(
    () => paginateRows(staticRows, page, pageSize),
    [staticRows, page, pageSize],
  );

  const loading = staticMode ? (props.loading ?? false) : remoteQuery.loading;
  const fetching = staticMode ? false : remoteQuery.fetching;
  const rows = staticMode ? staticPageRows : remoteQuery.rows;
  const total = staticMode ? staticRows.length : remoteQuery.total;

  useEffect(() => {
    setPage(1);
  }, [sort, pageSize, staticRowsSource, remoteFilters, citationSearch, filterDomain]);

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
      <PaginatedTableCard
      loading={loading}
      fetching={fetching}
      footer={
        total > 0 ? (
          <TablePagination
            total={total}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
          />
        ) : null
      }
    >
        <table className="w-full min-w-[1040px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: "34%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "12%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
          </colgroup>
          <thead className="text-muted-foreground bg-background/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5 pr-10">URL</th>
              <th>
                <span className="inline-flex items-center gap-1">
                  平台
                  <ColumnHelp
                    label="平台"
                    description="AI 回复中直接引用此链接的平台。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  是否提及
                  <ColumnHelp
                    label="是否提及"
                    description="AI 回复中直接提及的品牌。"
                  />
                </span>
              </th>
              <th>
                <span className="inline-flex items-center gap-1">
                  提及品牌
                  <ColumnHelp
                    label="提及品牌"
                    description="AI 回复中直接提及的品牌。"
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
            {loading && rows.length === 0 ? (
              <SkeletonRows />
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无 URL 数据
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.url}
                  className={cn(wideTableRowClass, "cursor-pointer")}
                  onClick={() => openPromptsDialog(row)}
                >
                  <td className="max-w-0 pl-5 pr-10">
                    <UrlCell url={row.url} title={citationUrlDisplayTitle(row.title, row.url)} />
                  </td>
                  <td className="px-4" onClick={(event) => event.stopPropagation()}>
                    <PlatformLogoGroup
                      providers={row.platforms ?? []}
                      logoClassName="size-5"
                    />
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
    </PaginatedTableCard>
    </>
  );
}
