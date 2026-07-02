import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  platformMatrixSkeletonGridColumns,
  platformMatrixTableClasses,
  platformMatrixTableMinWidth,
  PLATFORM_MATRIX_PLATFORM_COLUMN_MIN,
  PLATFORM_MATRIX_ROW_COLUMN_MIN,
} from "@/components/analysis/platform/platformMatrixTableLayout";
import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { DeltaBadgeSlot } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { PlatformMatrixMetricDefinition } from "@/lib/analysis/platform";
import type { PlatformMatrixRow } from "@/lib/analysis/platform";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { usePlatformCatalog } from "@/hooks/usePlatformCatalog";
import type { PlatformMatrixRowDimension } from "@/types";

type PlatformMatrixTableProps = {
  rowDimension: PlatformMatrixRowDimension;
  metric: PlatformMatrixMetricDefinition;
  rows: PlatformMatrixRow[];
  platforms: string[];
  loading?: boolean;
};

type PlatformColumnSort = {
  platformId: string;
  dir: "asc" | "desc";
};

type SortMode = PlatformColumnSort["dir"] | "default";

function compareMatrixValues(
  a: number | null | undefined,
  b: number | null | undefined,
  dir: PlatformColumnSort["dir"],
): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  const diff = a - b;
  return dir === "asc" ? diff : -diff;
}

function cyclePlatformSort(current: PlatformColumnSort | null, platformId: string): PlatformColumnSort | null {
  if (!current || current.platformId !== platformId) {
    return { platformId, dir: "desc" };
  }
  if (current.dir === "desc") {
    return { platformId, dir: "asc" };
  }
  return null;
}

function sortRowsByPlatform(
  rows: PlatformMatrixRow[],
  sort: PlatformColumnSort | null,
): PlatformMatrixRow[] {
  if (!sort) return rows;
  return [...rows].sort((a, b) =>
    compareMatrixValues(a.values[sort.platformId], b.values[sort.platformId], sort.dir),
  );
}

function PlatformMatrixSkeleton({
  rowDimension,
  platformCount,
}: {
  rowDimension: PlatformMatrixRowDimension;
  platformCount: number;
}) {
  const rowLabel = rowDimension === "competitor" ? "竞争对手" : "主题";
  const gridColumns = platformMatrixSkeletonGridColumns(platformCount);

  return (
    <div className="space-y-0" aria-hidden>
      <div
        className={platformMatrixTableClasses.skeletonHeader}
        style={{ gridTemplateColumns: gridColumns }}
      >
        <div className="px-5">
          <Skeleton className="h-4 w-16" />
        </div>
        {Array.from({ length: Math.max(platformCount, 1) }).map((_, index) => (
          <div key={index} className="flex justify-start px-4">
            <Skeleton className="size-5 rounded-md" />
          </div>
        ))}
      </div>
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className={platformMatrixTableClasses.skeletonRow}
          style={{ gridTemplateColumns: gridColumns }}
        >
          <div className="px-5">
            <Skeleton className="h-4 w-28" />
          </div>
          {Array.from({ length: Math.max(platformCount, 1) }).map((_, cellIndex) => (
            <div key={cellIndex} className="flex justify-start px-4">
              <Skeleton className="h-4 w-10" />
            </div>
          ))}
        </div>
      ))}
      <span className="sr-only">{rowLabel}</span>
    </div>
  );
}

type PlatformColumnHeaderProps = {
  platformId: string;
  label: string;
  sortMode: SortMode;
  onClick: () => void;
};

function PlatformColumnHeader({ platformId, label, sortMode, onClick }: PlatformColumnHeaderProps) {
  const sortIcon =
    sortMode === "asc" ? (
      <ChevronUp className="text-primary size-3 shrink-0" aria-hidden />
    ) : sortMode === "desc" ? (
      <ChevronDown className="text-primary size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="text-muted-foreground size-3 shrink-0" aria-hidden />
    );

  return (
    <button
      type="button"
      className="inline-flex w-full items-center justify-start mt-1 rounded-md transition-colors"
      aria-label={`按 ${label} 排序`}
      aria-sort={sortMode === "default" ? "none" : sortMode === "asc" ? "ascending" : "descending"}
      onClick={onClick}
    >
      <PlatformLogo provider={platformId} label={label} className="size-5 shrink-0" />
      <span className="inline-flex items-center gap-1 mt-1 ml-1.5">
        <span className="text-muted-foreground max-w-[7rem] truncate text-xs leading-none">{label}</span>
        {sortIcon}
      </span>
    </button>
  );
}

export function PlatformMatrixTable({
  rowDimension,
  metric,
  rows,
  platforms,
  loading = false,
}: PlatformMatrixTableProps) {
  const platformCatalog = usePlatformCatalog();
  const rowHeader = rowDimension === "competitor" ? "竞争对手" : "主题";
  const scrollMinWidth = platformMatrixTableMinWidth(platforms.length);
  const [columnSort, setColumnSort] = useState<PlatformColumnSort | null>(null);

  useEffect(() => {
    setColumnSort(null);
  }, [metric.id, rowDimension]);

  const sortedRows = useMemo(() => sortRowsByPlatform(rows, columnSort), [rows, columnSort]);

  function handlePlatformHeaderClick(platformId: string) {
    setColumnSort((current) => cyclePlatformSort(current, platformId));
  }

  function sortModeForPlatform(platformId: string): SortMode {
    if (!columnSort || columnSort.platformId !== platformId) return "default";
    return columnSort.dir;
  }

  return (
    <section className="border-border overflow-hidden rounded-lg border bg-muted-background" aria-busy={loading}>
      <div className="overflow-x-auto">
        <table
          className="w-full table-fixed text-sm"
          style={{ minWidth: scrollMinWidth }}
        >
          <colgroup>
            <col style={{ width: PLATFORM_MATRIX_ROW_COLUMN_MIN }} />
            {platforms.map((platform) => (
              <col key={platform} style={{ width: PLATFORM_MATRIX_PLATFORM_COLUMN_MIN }} />
            ))}
          </colgroup>
          <thead className="text-muted-foreground bg-background/80 text-left">
            <tr className="[&>th]:align-middle [&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2 [&>th]:font-medium">
              <th className="pl-5">{rowHeader}</th>
              {platforms.map((platform) => {
                const meta = resolvePlatformMeta(platform, platformCatalog);
                return (
                  <th key={platform} className="align-middle">
                    <PlatformColumnHeader
                      platformId={meta.platform}
                      label={meta.label}
                      sortMode={sortModeForPlatform(platform)}
                      onClick={() => handlePlatformHeaderClick(platform)}
                    />
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={platforms.length + 1} className="p-0">
                  <PlatformMatrixSkeleton rowDimension={rowDimension} platformCount={platforms.length} />
                </td>
              </tr>
            ) : sortedRows.length === 0 || platforms.length === 0 ? (
              <tr>
                <td
                  colSpan={Math.max(platforms.length, 1) + 1}
                  className="text-muted-foreground px-5 py-10 text-center text-sm"
                >
                  暂无矩阵数据
                </td>
              </tr>
            ) : (
              sortedRows.map((row) => (
                <tr key={row.id} className={platformMatrixTableClasses.row}>
                  <td className="min-w-0 overflow-hidden pl-5 whitespace-normal">
                    {rowDimension === "competitor" ? (
                      <BrandRankLabel
                        label={row.label}
                        domain={row.domain}
                        size="sm"
                        isOwn={row.isOwn}
                        isFocus={row.isFocus}
                      />
                    ) : (
                      <span className="font-medium">{row.label}</span>
                    )}
                  </td>
                  {platforms.map((platform) => {
                    const value = row.values[platform];
                    const previousValue = row.previousValues[platform];
                    const delta = metric.formatDelta(value, previousValue);
                    return (
                      <td key={platform} className="text-foreground text-left font-medium tabular-nums">
                        {value == null ? (
                          "-"
                        ) : (
                          <div className="inline-flex items-center gap-1.5">
                            <span>{metric.formatValue(value)}</span>
                            <DeltaBadgeSlot delta={delta} />
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
