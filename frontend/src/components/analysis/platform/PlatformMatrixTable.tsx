import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import {
  platformMatrixSkeletonGridColumns,
  platformMatrixTableMinWidth,
  PLATFORM_MATRIX_PLATFORM_COLUMN_MIN,
  PLATFORM_MATRIX_ROW_COLUMN_MIN,
} from "@/components/analysis/platform/platformMatrixTableLayout";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { PlatformMatrixMetricDefinition } from "@/lib/analysis/platform";
import type { PlatformMatrixRow } from "@/lib/analysis/platform";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type { PlatformMatrixRowDimension, SamplingPlatform } from "@/types";

type PlatformMatrixTableProps = {
  rowDimension: PlatformMatrixRowDimension;
  metric: PlatformMatrixMetricDefinition;
  rows: PlatformMatrixRow[];
  platforms: string[];
  platformsMeta: SamplingPlatform[];
  onSelectPlatform: (platformId: string) => void;
  loading?: boolean;
};

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
        className="border-border grid items-center border-b py-3"
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
          className="border-border grid items-center border-t py-3"
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

export function PlatformMatrixTable({
  rowDimension,
  metric,
  rows,
  platforms,
  platformsMeta,
  onSelectPlatform,
  loading = false,
}: PlatformMatrixTableProps) {
  const rowHeader = rowDimension === "competitor" ? "竞争对手" : "主题";
  const scrollMinWidth = platformMatrixTableMinWidth(platforms.length);

  return (
    <section className="border-border overflow-hidden rounded-lg border bg-white" aria-busy={loading}>
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
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:align-middle [&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-3 [&>th]:font-medium">
              <th className="pl-5">{rowHeader}</th>
              {platforms.map((platform) => {
                const meta = resolvePlatformMeta(platform, platformsMeta);
                return (
                  <th key={platform} className="text-left align-middle">
                    <button
                      type="button"
                      className="text-foreground flex w-full items-center justify-start gap-1.5 rounded-md transition-colors"
                      onClick={() => onSelectPlatform(platform)}
                    >
                      <PlatformLogo
                        provider={meta.platform}
                        label={meta.label}
                        className="block size-5 shrink-0"
                      />
                      <span className="text-xs leading-5 h-4">{meta.label}</span>
                    </button>
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
            ) : rows.length === 0 || platforms.length === 0 ? (
              <tr>
                <td
                  colSpan={Math.max(platforms.length, 1) + 1}
                  className="text-muted-foreground px-5 py-10 text-center text-sm"
                >
                  暂无矩阵数据
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-border border-t [&>td]:align-middle [&>td]:whitespace-nowrap [&>td]:px-4 [&>td]:py-2.5"
                >
                  <td className="pl-5">
                    {rowDimension === "competitor" ? (
                      <div className="flex items-center gap-2">
                        <BrandRankIcon label={row.label} size="sm" />
                        <span className="font-medium">{row.label}</span>
                        {row.isOwn ? (
                          <Badge variant="orange" className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium">
                            拥有
                          </Badge>
                        ) : null}
                      </div>
                    ) : (
                      <span className="font-medium">{row.label}</span>
                    )}
                  </td>
                  {platforms.map((platform) => {
                    const value = row.values[platform];
                    return (
                      <td key={platform} className="text-foreground text-left font-medium tabular-nums">
                        {value == null ? "-" : metric.formatValue(value)}
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
