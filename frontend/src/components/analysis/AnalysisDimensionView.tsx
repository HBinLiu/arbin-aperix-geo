import { AnalysisRankTable, type RankRow } from "@/components/analysis/AnalysisRankTable";
import { MetricTrendCard } from "@/components/analysis/MetricTrendCard";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis";
import type { AnalysisDimension } from "@/types";

type AnalysisDimensionViewProps = {
  dimension: AnalysisDimension;
  multiSeries?: { date: string; values: Record<string, number> }[];
  singleSeries?: { date: string; value: number | null }[];
  compareSeries?: { date: string; values: Record<string, number> }[];
  labels?: string[];
  visibleLabels?: Set<string>;
  onToggleLabel?: (label: string) => void;
  showCompare?: boolean;
  onToggleCompare?: (checked: boolean) => void;
  valueFormatter?: (v: number) => string;
  rankHeader: string;
  rankRows: RankRow[];
};

export function AnalysisDimensionView({
  dimension,
  multiSeries,
  singleSeries,
  compareSeries,
  labels,
  visibleLabels,
  onToggleLabel,
  showCompare,
  onToggleCompare,
  valueFormatter,
  rankHeader,
  rankRows,
}: AnalysisDimensionViewProps) {
  const meta = ANALYSIS_DIMENSIONS.find((d) => d.id === dimension)!;

  const ownRow = rankRows.find((row) => row.isOwn);

  return (
    <>
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight">{meta.label}</h2>
        <p className="text-muted-foreground mt-1 text-sm">{meta.description}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <MetricTrendCard
          title={meta.label}
          value={ownRow?.value}
          delta={ownRow?.delta}
          multiSeries={multiSeries}
          singleSeries={singleSeries}
          labels={labels}
          visibleLabels={visibleLabels}
          onToggleLabel={onToggleLabel}
          compareSeries={compareSeries}
          showCompare={showCompare}
          onToggleCompare={onToggleCompare}
          valueFormatter={valueFormatter}
        />
        <AnalysisRankTable title={`${meta.label}排名`} valueHeader={rankHeader} rows={rankRows} />
      </div>
    </>
  );
}
