import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatDelta } from "@/lib/analysis/format";
import type { SamplingPlatform } from "@/types";

type DeltaFormatter = (
  current: number | null | undefined,
  previous: number | null | undefined,
) => string | null;

export function buildBrandRankRows(
  current: Record<string, number | null | undefined>,
  previous: Record<string, number | null | undefined> | undefined,
  ownLabel: string,
  formatter: (v: number | null | undefined) => string,
  deltaFormatter: DeltaFormatter = formatDelta,
): RankRow[] {
  return Object.keys(current)
    .sort((a, b) => (current[b] ?? -1) - (current[a] ?? -1))
    .map((label) => {
      const valueNum = current[label];
      const previousValue = previous?.[label];
      return {
        id: label,
        label,
        value: formatter(valueNum),
        valueNum: valueNum ?? undefined,
        delta: deltaFormatter(valueNum ?? undefined, previousValue ?? undefined),
        deltaSortNum: previousValue != null && valueNum != null ? valueNum - previousValue : null,
        isOwn: label === ownLabel,
      };
    });
}

export function resolvePlatformMeta(
  platform: string,
  catalog: SamplingPlatform[],
): SamplingPlatform {
  return catalog.find((item) => item.platform === platform) ?? { platform, label: platform };
}
