import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { FaviconImage } from "@/components/common/FaviconImage";
import { DotBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacklinkOpportunityUrls } from "@/hooks/useBacklinkOpportunityDetail";
import { citationMentionsOwnBrand, citationUrlDisplayTitle } from "@/lib/analysis/citation";
import { cn } from "@/lib/utils";
import type { AnalysisFilters, BacklinkOpportunityUrlRow, CitationUrlSortField, SamplingPlatform } from "@/types";

const SKELETON_ROWS = 8;
const COLUMN_COUNT = 5;

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

type SortableHeaderProps = {
  label: string;
  sortKey: UrlSortKey;
  sort: UrlSortState;
  onSort: (key: UrlSortKey) => void;
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

type OpportunityBacklinkUrlTableProps = {
  subjectId: string;
  host: string;
  filters: AnalysisFilters;
  ownLabel: string;
  ownBrand?: string | null;
  platformsMeta: SamplingPlatform[];
};

export function OpportunityBacklinkUrlTable({
  subjectId,
  host,
  filters,
  ownLabel,
  ownBrand,
  platformsMeta,
}: OpportunityBacklinkUrlTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<UrlSortState>(null);
  const { sortBy, order } = urlSortParams(sort);

  const { rows, total, isLoading } = useBacklinkOpportunityUrls(subjectId, filters, {
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
        <table className="w-full min-w-[840px] table-fixed text-sm">
          <colgroup>
            <col style={{ width: "35%" }} />
            <col style={{ width: "15%" }} />
            <col style={{ width: "15%" }} />
            <col style={{ width: "20%" }} />
            <col style={{ width: "15%" }} />
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5 pr-10">URL</th>
              <th>
                <SortableHeader
                  label="引用次数"
                  sortKey="count"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleUrlSort(prev, key))}
                />
              </th>
              <th>平台</th>
              <th>页面内</th>
              <th>是否提及</th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {isLoading ? (
              <SkeletonRows />
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无 URL 数据
                </td>
              </tr>
            ) : (
              rows.map((row: BacklinkOpportunityUrlRow) => (
                <tr key={row.url} className="border-border border-t [&>td]:py-3">
                  <td className="max-w-0 pl-5 pr-10">
                    <UrlCell url={row.url} title={citationUrlDisplayTitle(row.title, row.url)} />
                  </td>
                  <td className="px-4 font-semibold tabular-nums">{row.count}</td>
                  <td className="px-4">
                    <PlatformLogoGroup
                      providers={row.platforms}
                      platforms={platformsMeta}
                      logoClassName="size-5"
                    />
                  </td>
                  <td className="px-4">
                    <MentionedBrandsCell brands={row.mentioned_brands} />
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
