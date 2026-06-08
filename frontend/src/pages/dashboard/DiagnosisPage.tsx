import { useEffect, useMemo, useState } from "react";
import { MessageSquare, MessagesSquare } from "lucide-react";

import { DiagnosisDimensionCard } from "@/components/diagnosis/DiagnosisDimensionCard";
import { DiagnosisMentionTable } from "@/components/diagnosis/DiagnosisMentionTable";
import { DiagnosisPrioritySelect } from "@/components/diagnosis/DiagnosisPrioritySelect";
import { DiagnosisPromptTable } from "@/components/diagnosis/DiagnosisPromptTable";
import { DiagnosisScoreGauge } from "@/components/diagnosis/DiagnosisScoreGauge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useDiagnosis } from "@/hooks/useDiagnosis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import {
  DIAGNOSIS_TABS,
  filterDiagnosisByPriority,
  type DiagnosisPriorityFilter,
  type DiagnosisTab,
} from "@/lib/diagnosis";

type DiagnosisContentProps = {
  subjectId: string;
};

/** 诊断中心：得分概览、维度摘要与诊断明细表 */
export function DiagnosisContent({ subjectId }: DiagnosisContentProps) {
  const { subject } = useDashboardContext();
  const { platforms } = useAnalysisFilter();
  const [activeTab, setActiveTab] = useState<DiagnosisTab>("mention");
  const [priorityFilter, setPriorityFilter] = useState<DiagnosisPriorityFilter>("all");

  useEffect(() => {
    setPriorityFilter("all");
  }, [subject.id]);

  const { isLoading, overview, mentionRows, promptRows } = useDiagnosis(
    subjectId,
    DEFAULT_ANALYSIS_FILTERS,
  );

  const filteredMentionRows = useMemo(
    () => filterDiagnosisByPriority(mentionRows, priorityFilter),
    [mentionRows, priorityFilter],
  );
  const filteredPromptRows = useMemo(
    () => filterDiagnosisByPriority(promptRows, priorityFilter),
    [promptRows, priorityFilter],
  );

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <div className="grid gap-4 xl:grid-cols-[minmax(240px,0.9fr)_1.1fr_1.1fr]">
          <DiagnosisScoreGauge
            score={overview.overallScore}
            status={overview.overallStatus}
            loading={isLoading}
          />
          <DiagnosisDimensionCard
            title="AI提及与平均排名"
            description="当向 AI 提出相关问题时，品牌被提及的频率及其在回答中的排名"
            icon={MessagesSquare}
            healthScore={overview.mention.health_score}
            priorityCounts={overview.mention.priority_counts}
            active={activeTab === "mention"}
            loading={isLoading}
          />
          <DiagnosisDimensionCard
            title="提示词"
            description="提示词在 AI 回复中的可见度与问题类型分布"
            icon={MessageSquare}
            healthScore={overview.prompt.health_score}
            priorityCounts={overview.prompt.priority_counts}
            active={activeTab === "prompt"}
            loading={isLoading}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as DiagnosisTab)}>
            <TabsList>
              {DIAGNOSIS_TABS.map((tab) => (
                <TabsTrigger key={tab.id} value={tab.id}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <DiagnosisPrioritySelect value={priorityFilter} onChange={setPriorityFilter} />
        </div>

        {activeTab === "mention" ? (
          <DiagnosisMentionTable rows={filteredMentionRows} platformsMeta={platforms} loading={isLoading} />
        ) : (
          <DiagnosisPromptTable rows={filteredPromptRows} loading={isLoading} />
        )}
      </div>
    </div>
  );
}
