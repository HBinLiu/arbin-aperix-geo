import { useEffect, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { VisibilityMetricSection } from "@/components/analysis/visibility/VisibilityMetricSection";
import { OverviewMetricCard } from "@/components/dashboard/OverviewMetricCard";
import { OverviewSentimentCard } from "@/components/dashboard/OverviewSentimentCard";
import { OverviewTopicSection } from "@/components/dashboard/OverviewTopicSection";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useDashboardOverview } from "@/hooks/useDashboardOverview";
import {
  ANALYSIS_FILTER_ALL,
  DEFAULT_ANALYSIS_FILTERS,
  formatRate,
  VISIBILITY_METRICS,
} from "@/lib/analysis";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis/nav";
import { brandRankSubtitle } from "@/lib/dashboard/overview";
import type { AnalysisFilters } from "@/types";

const VISIBILITY_DEF = VISIBILITY_METRICS.find((m) => m.id === "visibility")!;
const SHARE_VOICE_DEF = VISIBILITY_METRICS.find((m) => m.id === "shareVoice")!;
const CITATION_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "citation")!;
const SENTIMENT_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "sentiment")!;

type OverviewContentProps = {
  subjectId: string;
};

/** 控制台概述：核心指标、可见度趋势与主题表现。 */
export function OverviewContent({ subjectId }: OverviewContentProps) {
  const { subject } = useDashboardContext();
  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const {
    isLoading,
    overview,
    ownLabel,
    topLabels,
    visibilityMetric,
    topicRows,
    ranks,
  } = useDashboardOverview(subjectId, filters);

  const visibilityValue =
    overview?.visibility_rate != null ? formatRate(overview.visibility_rate) : "-";
  const citationValue =
    overview?.citation_rate != null ? formatRate(overview.citation_rate) : "-";
  const shareVoiceValue =
    overview?.share_voice != null ? formatRate(overview.share_voice) : "-";

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="bg-muted/30 flex flex-col gap-4 px-4 py-4 sm:px-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewMetricCard
            title="可见度"
            description={VISIBILITY_DEF.description}
            value={visibilityValue}
            rankSubtitle={brandRankSubtitle(ranks.visibility)}
            tag={ranks.visibility != null ? { type: "rank", rank: ranks.visibility } : null}
            loading={isLoading}
          />
          <OverviewMetricCard
            title="引用率"
            description={CITATION_META.description}
            value={citationValue}
            rankSubtitle={brandRankSubtitle(ranks.citation)}
            tag={
              ranks.citation != null && ranks.citation > 1
                ? { type: "improve" }
                : ranks.citation === 1
                  ? { type: "rank", rank: 1 }
                  : null
            }
            loading={isLoading}
          />
          <OverviewMetricCard
            title="声量份额"
            description={SHARE_VOICE_DEF.description}
            value={shareVoiceValue}
            rankSubtitle={brandRankSubtitle(ranks.shareVoice)}
            tag={ranks.shareVoice != null ? { type: "rank", rank: ranks.shareVoice } : null}
            loading={isLoading}
          />
          <OverviewSentimentCard
            description={SENTIMENT_META.description}
            score={overview?.sentiment_score}
            loading={isLoading}
          />
        </div>

        <VisibilityMetricSection
          definition={VISIBILITY_DEF}
          metric={visibilityMetric}
          topLabels={topLabels}
          ownLabel={ownLabel}
          scopeKey={`${subjectId}:overview-visibility`}
          loading={isLoading}
        />

        <OverviewTopicSection rows={topicRows} loading={isLoading} />
      </div>
    </>
  );
}
