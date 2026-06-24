import { useMemo } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { VisibilityMetricSection } from "@/components/analysis/visibility/VisibilityMetricSection";
import { OverviewMetricCard } from "@/components/dashboard/OverviewMetricCard";
import { OverviewTopicSection } from "@/components/dashboard/OverviewTopicSection";
import { SamplingProgressOverview } from "@/components/dashboard/SamplingProgressOverview";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDashboardOverview } from "@/hooks/useDashboardOverview";
import { useSubjectPipeline } from "@/hooks/useSubjectPipeline";
import {
  entityChartLabels,
  formatRate,
  VISIBILITY_METRICS,
} from "@/lib/analysis";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis/nav";
import { brandRankBadge, brandRankSubtitle } from "@/lib/dashboard/overview";

const VISIBILITY_DEF = VISIBILITY_METRICS.find((m) => m.id === "visibility")!;
const SHARE_VOICE_DEF = VISIBILITY_METRICS.find((m) => m.id === "shareVoice")!;
const CITATION_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "citation")!;
const SENTIMENT_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "sentiment")!;

type OverviewContentProps = {
  subjectId: string;
};

/** 控制台概述：采样未完成时展示进度；完成后展示核心指标、可见度趋势与主题表现。 */
export function OverviewContent({ subjectId }: OverviewContentProps) {
  const pipeline = useSubjectPipeline();
  const showMetrics = pipeline.canShowMetrics;

  if (!showMetrics) {
    return <SamplingProgressOverview subjectId={subjectId} pipeline={pipeline} />;
  }

  return <OverviewMetricsContent subjectId={subjectId} />;
}

function OverviewMetricsContent({ subjectId }: { subjectId: string }) {
  const { filters, setFilters } = useAnalysisFiltersState();
  const { entities } = useAnalysisFilter();
  const entityLabels = useMemo(() => entityChartLabels(entities), [entities]);

  const { isLoading, metrics, focusLabel, visibilityMetric, topicRows } =
    useDashboardOverview(subjectId, filters, entities);

  const { visibility, citation, shareVoice, sentiment } = metrics;

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="bg-muted/30 flex flex-col gap-4 px-4 py-4 sm:px-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewMetricCard
            title="可见度"
            description={VISIBILITY_DEF.description}
            value={formatRate(visibility.current)}
            deltaCurrent={visibility.current}
            deltaPrevious={visibility.previous}
            deltaFormat="percent"
            bottomLeft={brandRankSubtitle(visibility.rank)}
            bottomRight={brandRankBadge(visibility.rank)}
            loading={isLoading}
          />
          <OverviewMetricCard
            title="引用率"
            description={CITATION_META.description}
            value={formatRate(citation.current)}
            deltaCurrent={citation.current}
            deltaPrevious={citation.previous}
            deltaFormat="percent"
            bottomLeft={brandRankSubtitle(citation.rank)}
            bottomRight={brandRankBadge(citation.rank)}
            loading={isLoading}
          />
          <OverviewMetricCard
            title="声量份额"
            description={SHARE_VOICE_DEF.description}
            value={formatRate(shareVoice.current)}
            deltaCurrent={shareVoice.current}
            deltaPrevious={shareVoice.previous}
            deltaFormat="percent"
            bottomLeft={brandRankSubtitle(shareVoice.rank)}
            bottomRight={brandRankBadge(shareVoice.rank)}
            loading={isLoading}
          />
          <OverviewMetricCard
            title="情感倾向"
            description={SENTIMENT_META.description}
            value={sentiment.current}
            sentimentLabel={sentiment.label}
            deltaCurrent={sentiment.current}
            deltaPrevious={sentiment.previous}
            deltaFormat="sentiment"
            bottomLeft={brandRankSubtitle(sentiment.rank)}
            bottomRight={brandRankBadge(sentiment.rank)}
            loading={isLoading}
          />
        </div>

        <VisibilityMetricSection
          definition={VISIBILITY_DEF}
          metric={visibilityMetric}
          topLabels={entityLabels}
          ownLabel={focusLabel}
          scopeKey={`${subjectId}:overview-visibility`}
          loading={isLoading}
        />

        <OverviewTopicSection rows={topicRows} loading={isLoading} />
      </div>
    </>
  );
}
