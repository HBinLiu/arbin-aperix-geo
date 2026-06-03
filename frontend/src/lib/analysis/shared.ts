import type { RankRow } from "@/components/analysis/AnalysisRankTable";
import { formatDelta } from "@/lib/analysis/format";
import type { SamplingPlatform } from "@/types";

export function buildBrandRankRows(
  current: Record<string, number>,
  previous: Record<string, number> | undefined,
  ownLabel: string,
  formatter: (v: number) => string,
): RankRow[] {
  return Object.keys(current)
    .sort((a, b) => (current[b] ?? 0) - (current[a] ?? 0))
    .map((label) => ({
      id: label,
      label,
      value: formatter(current[label] ?? 0),
      delta: formatDelta(current[label], previous?.[label]),
      isOwn: label === ownLabel,
    }));
}

export function resolvePlatformMeta(platform: string, platforms: SamplingPlatform[]): SamplingPlatform {
  const exact = platforms.find((p) => p.platform === platform);
  if (exact) return exact;
  return { platform, label: platform };
}
