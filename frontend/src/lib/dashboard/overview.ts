import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";

/** 自有品牌在排名表中的位次（1 起），未上榜则 null */
export function ownBrandRank(rows: RankRow[]): number | null {
  const idx = rows.findIndex((row) => row.isOwn);
  return idx >= 0 ? idx + 1 : null;
}

export function brandRankSubtitle(rank: number | null | undefined): string | null {
  if (rank == null) return null;
  return `所有品牌第 ${rank} 名`;
}
