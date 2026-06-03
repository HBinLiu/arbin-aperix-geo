import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AnalysisFilterBar } from "@/components/analysis/AnalysisFilterBar";
import { AnalysisRankTable } from "@/components/analysis/AnalysisRankTable";
import { MetricTrendCard } from "@/components/analysis/MetricTrendCard";
import { FaviconImage } from "@/components/common/FaviconImage";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { fetchDailyVisibility, fetchRank } from "@/api/analysis";
import {
  ANALYSIS_DIMENSIONS,
  buildBrandRankRows,
  dateRangeDays,
  formatDelta,
  formatRate,
  previousDateRange,
  ANALYSIS_FILTER_ALL,
  DEFAULT_ANALYSIS_FILTERS,
  toAnalysisQueryFilters,
} from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

function looksLikeDomain(label: string): boolean {
  return /\.[a-z]{2,}/i.test(label);
}

function rankRowIcon(label: string) {
  if (!looksLikeDomain(label)) return undefined;
  return (
    <FaviconImage domain={label} size={24} className="size-6 rounded-md" iconClassName="size-3.5" />
  );
}

/** 分析 · 可见度 */
export function VisibilityPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);
  const [showCompare, setShowCompare] = useState(false);
  const [showCurrentPeriod, setShowCurrentPeriod] = useState(true);
  const [showPreviousPeriod, setShowPreviousPeriod] = useState(true);
  const [visibleLabels, setVisibleLabels] = useState<Set<string>>(new Set());

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const prevRange = useMemo(() => previousDateRange(from, to), [from, to]);
  const { topicId, platformId } = queryFilters;

  const filterBar = (
    <AnalysisFilterBar value={filters} onChange={setFilters} />
  );

  const rankQuery = useQuery({
    queryKey: queryKeys.analysisRank(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchRank(subjectId, from, to, queryFilters),
  });

  const prevRankQuery = useQuery({
    queryKey: queryKeys.analysisRank(
      subjectId,
      prevRange.from,
      prevRange.to,
      topicId,
      platformId,
    ),
    queryFn: () => fetchRank(subjectId, prevRange.from, prevRange.to, queryFilters),
  });

  const dailyQuery = useQuery({
    queryKey: queryKeys.analysisDailyVisibility(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchDailyVisibility(subjectId, from, to, queryFilters),
  });

  const prevDailyQuery = useQuery({
    queryKey: queryKeys.analysisDailyVisibility(
      subjectId,
      prevRange.from,
      prevRange.to,
      topicId,
      platformId,
    ),
    queryFn: () => fetchDailyVisibility(subjectId, prevRange.from, prevRange.to, queryFilters),
    enabled: showCompare,
  });

  const chartLabels = useMemo(
    () => dailyQuery.data?.labels.slice(0, 5) ?? [],
    [dailyQuery.data],
  );

  const effectiveVisibleLabels = useMemo(() => {
    if (visibleLabels.size > 0) return visibleLabels;
    return new Set(chartLabels);
  }, [visibleLabels, chartLabels]);

  const toggleLabel = (label: string) => {
    setVisibleLabels((prev) => {
      const base = prev.size > 0 ? new Set(prev) : new Set(chartLabels);
      if (base.has(label)) base.delete(label);
      else base.add(label);
      return base;
    });
  };

  const isLoading = rankQuery.isLoading || dailyQuery.isLoading;

  const meta = ANALYSIS_DIMENSIONS.find((d) => d.id === "visibility")!;
  const pageHeader = (
    <div>
      <h2 className="text-xl font-semibold tracking-tight">{meta.label}</h2>
      <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">{meta.description}</p>
    </div>
  );

  const metricsCard = (
    rankRows: ReturnType<typeof buildBrandRankRows>,
    ownVisibility: number | undefined,
    prevOwnVisibility: number | undefined,
  ) => (
    <div className="border-border overflow-hidden rounded-lg border bg-white">
      <div className="flex flex-col md:flex-row md:min-w-0">
        <div className="min-w-0 flex-1 p-5 md:min-w-[360px] md:shrink-0 md:flex-[1.6]">
          <MetricTrendCard
            embedded
            title={meta.label}
            value={formatRate(ownVisibility)}
            delta={formatDelta(ownVisibility, prevOwnVisibility)}
            multiSeries={dailyQuery.data?.series.map((p) => ({ date: p.date, values: p.values }))}
            labels={chartLabels}
            visibleLabels={effectiveVisibleLabels}
            onToggleLabel={toggleLabel}
            compareSeries={prevDailyQuery.data?.series.map((p) => ({ date: p.date, values: p.values }))}
            showCurrentPeriod={showCurrentPeriod}
            onToggleCurrentPeriod={setShowCurrentPeriod}
            showPreviousPeriod={showPreviousPeriod}
            onTogglePreviousPeriod={setShowPreviousPeriod}
            showCompare={showCompare}
            onToggleCompare={(checked) => {
              setShowCompare(checked);
              if (checked) setShowPreviousPeriod(true);
            }}
            valueFormatter={(v) => formatRate(v)}
          />
        </div>
        <div className="bg-border hidden w-px shrink-0 md:block" aria-hidden />
        <div className="flex min-w-0 flex-1 flex-col p-2 md:min-w-[180px] md:max-w-[560px] lg:max-w-[640px] md:shrink">
          <AnalysisRankTable
            embedded
            showMoreFooter
            className="max-h-[400px]"
            title={`${meta.label}排名`}
            valueHeader="可见度"
            rows={rankRows.map((row) => ({ ...row, icon: rankRowIcon(row.label) }))}
            emptyMessage="暂无数据"
          />
        </div>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <>
        {filterBar}
        <div className="px-4 pb-6">
          {pageHeader}
          <div className="border-border overflow-hidden rounded-lg border bg-white">
            <div className="bg-muted h-[360px] animate-pulse" />
          </div>
        </div>
      </>
    );
  }

  const rank = rankQuery.data;
  const ownLabel = rank?.own_label ?? dailyQuery.data?.own_label ?? "";
  const ownVisibility = ownLabel ? rank?.visibility_share[ownLabel] : undefined;
  const prevOwnVisibility = ownLabel ? prevRankQuery.data?.visibility_share[ownLabel] : undefined;
  const rankRows = rank
    ? buildBrandRankRows(
        rank.visibility_share,
        prevRankQuery.data?.visibility_share,
        ownLabel,
        (v) => formatRate(v),
      )
    : [];

  return (
    <>
      {filterBar}
      <div className="flex flex-col gap-4 px-6 py-4">
        {pageHeader}
        {metricsCard(rankRows, ownVisibility, prevOwnVisibility)}
      </div>
    </>
  );
}
