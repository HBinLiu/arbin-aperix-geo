import { useState } from "react";

import { SentimentResponseTable } from "@/components/analysis/sentiment/SentimentResponseTable";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SENTIMENT_TABS } from "@/lib/analysis/sentiment";
import type { AnalysisFilters, SamplingPlatform, SentimentTab } from "@/types";

type SentimentResponsesSectionProps = {
  subjectId: string;
  filters: AnalysisFilters;
  platformsMeta: SamplingPlatform[];
};

export function SentimentResponsesSection({
  subjectId,
  filters,
  platformsMeta,
}: SentimentResponsesSectionProps) {
  const [activeTab, setActiveTab] = useState<SentimentTab>("positive");

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as SentimentTab)}
      >
        <TabsList>
          {SENTIMENT_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <SentimentResponseTable
        subjectId={subjectId}
        filters={filters}
        activeTab={activeTab}
        platformsMeta={platformsMeta}
      />
    </div>
  );
}
